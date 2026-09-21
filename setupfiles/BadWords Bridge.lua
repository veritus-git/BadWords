--[[
    BadWords Bridge.lua
    ===================
    DaVinci Resolve Lua Bridge for BadWords.
    Enables communication with BadWords desktop app across all DaVinci Resolve
    versions (including DaVinci Resolve 21.1+ Free where Python scripting is removed
    and Lua sandbox is tightened).

    Runs completely within Resolve's Lua sandbox (no io, no ffi, no require).
    Uses loadfile for request input and fusion:SetPrefs/SavePrefs for response output.
]]

---@diagnostic disable: undefined-global

-- ---------------------------------------------------------------------------
-- 1. Pure Lua Base64 Encoder
-- ---------------------------------------------------------------------------
local B64_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
local function base64_encode(data)
    if not data or #data == 0 then return "" end
    return ((data:gsub(".", function(x)
        local r, b = "", x:byte()
        for i = 8, 1, -1 do
            r = r .. (b % 2 ^ i - b % 2 ^ (i - 1) >= 1 and "1" or "0")
        end
        return r
    end) .. "0000"):gsub("%d%d%d?%d?%d?%d?", function(x)
        if #x < 6 then return "" end
        local c = 0
        for i = 1, 6 do
            c = c + (x:sub(i, i) == "1" and 2 ^ (6 - i) or 0)
        end
        return B64_CHARS:sub(c + 1, c + 1)
    end) .. ({ "", "==", "=" })[#data % 3 + 1])
end

-- ---------------------------------------------------------------------------
-- 2. Pure Lua JSON Encoder & Decoder (dkjson 2.5 simplified)
-- ---------------------------------------------------------------------------
local json = {}

local pairs, type, tostring, tonumber = pairs, type, tostring, tonumber
local floor = math.floor
local strrep, gsub, strsub, strbyte, strchar = string.rep, string.gsub, string.sub, string.byte, string.char
local concat = table.concat

local function isarray(tbl)
    local max, n = 0, 0
    for k, v in pairs(tbl) do
        if type(k) ~= "number" or k < 1 or floor(k) ~= k then
            return false
        end
        if k > max then max = k end
        n = n + 1
    end
    if max > n * 2 then return false end
    return true, max
end

local escapecodes = {
    ["\""] = "\\\"", ["\\"] = "\\\\", ["\b"] = "\\b", ["\f"] = "\\f",
    ["\n"] = "\\n",  ["\r"] = "\\r",  ["\t"] = "\\t"
}

local function escapeutf8(uchar)
    local val = escapecodes[uchar]
    if val then return val end
    local cp = strbyte(uchar)
    if cp < 32 or cp == 127 then
        return string.format("\\u%04x", cp)
    end
    return uchar
end

function json.encode(val)
    local vtype = type(val)
    if vtype == "nil" then
        return "null"
    elseif vtype == "boolean" then
        return val and "true" or "false"
    elseif vtype == "number" then
        if val ~= val then return "null" end -- NaN
        if val >= math.huge or val <= -math.huge then return "null" end
        return tostring(val)
    elseif vtype == "string" then
        return '"' .. gsub(val, '[%z\1-\31\\"\127]', escapeutf8) .. '"'
    elseif vtype == "table" then
        local is_arr, arr_len = isarray(val)
        if is_arr then
            local parts = {}
            for i = 1, arr_len do
                parts[i] = json.encode(val[i])
            end
            return "[" .. concat(parts, ",") .. "]"
        else
            local parts = {}
            for k, v in pairs(val) do
                if type(k) == "string" or type(k) == "number" then
                    parts[#parts + 1] = json.encode(tostring(k)) .. ":" .. json.encode(v)
                end
            end
            return "{" .. concat(parts, ",") .. "}"
        end
    end
    return "null"
end

-- Minimal JSON Decoder
local function scan_white(str, pos)
    while pos <= #str do
        local c = strsub(str, pos, pos)
        if c == ' ' or c == '\t' or c == '\n' or c == '\r' then
            pos = pos + 1
        else
            break
        end
    end
    return pos
end

local scan_value

local function scan_string(str, pos)
    pos = pos + 1
    local start = pos
    local chars = {}
    while pos <= #str do
        local c = strsub(str, pos, pos)
        if c == '"' then
            chars[#chars + 1] = strsub(str, start, pos - 1)
            return concat(chars), pos + 1
        elseif c == '\\' then
            chars[#chars + 1] = strsub(str, start, pos - 1)
            pos = pos + 1
            local esc = strsub(str, pos, pos)
            if esc == '"' or esc == '\\' or esc == '/' then
                chars[#chars + 1] = esc
            elseif esc == 'b' then chars[#chars + 1] = '\b'
            elseif esc == 'f' then chars[#chars + 1] = '\f'
            elseif esc == 'n' then chars[#chars + 1] = '\n'
            elseif esc == 'r' then chars[#chars + 1] = '\r'
            elseif esc == 't' then chars[#chars + 1] = '\t'
            elseif esc == 'u' then
                local hex = strsub(str, pos + 1, pos + 4)
                if #hex == 4 then
                    local cp = tonumber(hex, 16)
                    if cp and cp < 128 then
                        chars[#chars + 1] = strchar(cp)
                    else
                        chars[#chars + 1] = "\\u" .. hex
                    end
                    pos = pos + 4
                end
            end
            pos = pos + 1
            start = pos
        else
            pos = pos + 1
        end
    end
    return nil, pos
end

local function scan_array(str, pos)
    pos = pos + 1
    local tbl = {}
    pos = scan_white(str, pos)
    if strsub(str, pos, pos) == ']' then return tbl, pos + 1 end
    while pos <= #str do
        local val
        val, pos = scan_value(str, pos)
        tbl[#tbl + 1] = val
        pos = scan_white(str, pos)
        local c = strsub(str, pos, pos)
        if c == ']' then return tbl, pos + 1 end
        if c ~= ',' then break end
        pos = scan_white(str, pos + 1)
    end
    return tbl, pos
end

local function scan_object(str, pos)
    pos = pos + 1
    local tbl = {}
    pos = scan_white(str, pos)
    if strsub(str, pos, pos) == '}' then return tbl, pos + 1 end
    while pos <= #str do
        pos = scan_white(str, pos)
        if strsub(str, pos, pos) ~= '"' then break end
        local key
        key, pos = scan_string(str, pos)
        pos = scan_white(str, pos)
        if strsub(str, pos, pos) ~= ':' then break end
        pos = scan_white(str, pos + 1)
        local val
        val, pos = scan_value(str, pos)
        tbl[key] = val
        pos = scan_white(str, pos)
        local c = strsub(str, pos, pos)
        if c == '}' then return tbl, pos + 1 end
        if c ~= ',' then break end
        pos = scan_white(str, pos + 1)
    end
    return tbl, pos
end

scan_value = function(str, pos)
    pos = scan_white(str, pos)
    local c = strsub(str, pos, pos)
    if c == '"' then
        return scan_string(str, pos)
    elseif c == '[' then
        return scan_array(str, pos)
    elseif c == '{' then
        return scan_object(str, pos)
    elseif c == 't' and strsub(str, pos, pos + 3) == 'true' then
        return true, pos + 4
    elseif c == 'f' and strsub(str, pos, pos + 4) == 'false' then
        return false, pos + 5
    elseif c == 'n' and strsub(str, pos, pos + 3) == 'null' then
        return nil, pos + 4
    else
        -- Number
        local start = pos
        while pos <= #str do
            local ch = strsub(str, pos, pos)
            if (ch >= '0' and ch <= '9') or ch == '-' or ch == '+' or ch == '.' or ch == 'e' or ch == 'E' then
                pos = pos + 1
            else
                break
            end
        end
        local num = tonumber(strsub(str, start, pos - 1))
        return num, pos
    end
end

function json.decode(str)
    if type(str) ~= "string" or #str == 0 then return nil end
    local ok, res = pcall(function()
        local v, _ = scan_value(str, 1)
        return v
    end)
    return ok and res or nil
end

-- ---------------------------------------------------------------------------
-- 3. Environment & Mailbox Detection
-- ---------------------------------------------------------------------------
local function detect_platform()
    local jit_global = rawget(_G, "jit")
    if jit_global and jit_global.os then
        local os_name = jit_global.os
        if os_name == "Windows" or os_name == "OSX" then
            return os_name
        end
        return "Linux"
    end
    if os.getenv("WINDIR") ~= nil then
        return "Windows"
    end
    if bmd.direxists("/Applications") then
        return "OSX"
    end
    return "Linux"
end

local platform = detect_platform()
local sep = (platform == "Windows") and "\\" or "/"

local function get_mailbox_dir()
    if platform == "Windows" then
        return (os.getenv("LOCALAPPDATA") or "") .. "\\BadWords\\resolve-bridge"
    elseif platform == "OSX" then
        return (os.getenv("HOME") or "") .. "/Library/Application Support/BadWords/resolve-bridge"
    else
        return (os.getenv("XDG_DATA_HOME") or ((os.getenv("HOME") or "") .. "/.local/share"))
            .. "/BadWords/resolve-bridge"
    end
end

local mailbox_dir = get_mailbox_dir()
local request_file = mailbox_dir .. sep .. "request.lua"

local fu = rawget(_G, "fusion") or rawget(_G, "fu")
if fu == nil then
    local r = rawget(_G, "resolve")
    if r and type(r.Fusion) == "function" then
        fu = r:Fusion()
    end
end

local res_app = rawget(_G, "resolve")
if res_app == nil and bmd and bmd.scriptapp then
    pcall(function() res_app = bmd.scriptapp("Resolve") end)
end

-- ---------------------------------------------------------------------------
-- 4. Bridge Response Helpers
-- ---------------------------------------------------------------------------
local function bridge_write(key, value)
    if not fu then return end
    for _ = 1, 5 do
        local ok = pcall(function()
            fu:SetPrefs(key, value)
            fu:SavePrefs()
        end)
        if ok then return end
        bmd.wait(0.05)
    end
end

local function bridge_ack(id)
    bridge_write("Global.BadWordsBridge.Ack", id)
end

local function bridge_respond(id, body_table)
    local body_json = json.encode(body_table or {})
    -- Escape non-ASCII bytes as \\uE0xx markers for ASCII safety
    local safe = body_json:gsub("[\128-\255]", function(c)
        return string.format("\\u%04x", 0xE000 + c:byte())
    end)
    bridge_write("Global.BadWordsBridge.Response", id .. ":" .. base64_encode(safe))
end

-- ---------------------------------------------------------------------------
-- 5. Resolve API Handlers for BadWords
-- ---------------------------------------------------------------------------
local handlers = rawget(_G, "BadWordsBridgeHandlers") or {}
_G.BadWordsBridgeHandlers = handlers

handlers.Ping = function()
    return { ok = true, message = "Pong", platform = platform }
end

handlers.GetTimelineInfo = function(req)
    if not res_app then
        return { error = "Resolve API object not available" }
    end
    local pm = res_app:GetProjectManager()
    if not pm then return { error = "GetProjectManager failed" } end
    local proj = pm:GetCurrentProject()
    if not proj then return { error = "No project open in DaVinci Resolve" } end

    local proj_name = proj:GetName() or ""
    local tl_count = proj:GetTimelineCount() or 0
    local timelines = {}
    for i = 1, tl_count do
        local tl = proj:GetTimelineByIndex(i)
        if tl then
            timelines[#timelines + 1] = tl:GetName() or ("Timeline " .. tostring(i))
        end
    end

    local current_tl = proj:GetCurrentTimeline()
    local current_tl_name = ""
    local fps = 24.0
    local start_frame = 0

    if current_tl then
        current_tl_name = current_tl:GetName() or ""
        fps = tonumber(current_tl:GetSetting("timelineFrameRate")) or 24.0
        start_frame = tonumber(current_tl:GetStartFrame()) or 0
    end

    return {
        ok = true,
        project = proj_name,
        current_timeline = current_tl_name,
        timelines = timelines,
        fps = fps,
        start_frame = start_frame
    }
end

handlers.GetAudioTracks = function(req)
    if not res_app then return { error = "Resolve API object not available" } end
    local pm = res_app:GetProjectManager()
    local proj = pm and pm:GetCurrentProject()
    if not proj then return { error = "No project open" } end

    local tl = proj:GetCurrentTimeline()
    if req and req.timeline_name and req.timeline_name ~= "" then
        local count = proj:GetTimelineCount() or 0
        for i = 1, count do
            local t = proj:GetTimelineByIndex(i)
            if t and t:GetName() == req.timeline_name then
                tl = t
                break
            end
        end
    end

    if not tl then return { error = "Timeline not found" } end

    local track_count = tl:GetTrackCount("audio") or 0
    local tracks = {}
    for i = 1, track_count do
        local t_name = tl:GetTrackName("audio", i) or ("Audio " .. tostring(i))
        tracks[#tracks + 1] = { index = i, name = t_name }
    end

    return { ok = true, tracks = tracks }
end

handlers.GetDirectAudioInfo = function(req)
    if not res_app then return { error = "Resolve API object not available" } end
    local pm = res_app:GetProjectManager()
    local proj = pm and pm:GetCurrentProject()
    if not proj then return { error = "No project open" } end

    local tl = proj:GetCurrentTimeline()
    if req and req.timeline_name and req.timeline_name ~= "" then
        local count = proj:GetTimelineCount() or 0
        for i = 1, count do
            local t = proj:GetTimelineByIndex(i)
            if t and t:GetName() == req.timeline_name then
                tl = t
                break
            end
        end
    end

    if not tl then return { error = "Timeline not found" } end

    local track_indices = req and req.track_indices
    if not track_indices or #track_indices == 0 then
        local total_tracks = tl:GetTrackCount("audio") or 0
        track_indices = {}
        for i = 1, total_tracks do track_indices[i] = i end
    end

    local clips = {}
    for _, tr_idx in ipairs(track_indices) do
        local items = tl:GetItemListInTrack("audio", tr_idx)
        if items then
            for _, item in ipairs(items) do
                local clip_name = item:GetName() or ""
                local start_f = item:GetStart()
                local end_f = item:GetEnd()
                local dur_f = item:GetDuration()
                local left_offset = 0
                pcall(function() left_offset = item:GetLeftOffset() or 0 end)
                local file_path = ""
                local mp_item = item:GetMediaPoolItem()
                if mp_item then
                    file_path = mp_item:GetClipProperty("File Path") or ""
                end
                clips[#clips + 1] = {
                    track_index = tr_idx,
                    name = clip_name,
                    start_frame = start_f,
                    end_frame = end_f,
                    duration = dur_f,
                    left_offset = left_offset,
                    file_path = file_path
                }
            end
        end
    end

    return { ok = true, clips = clips }
end

handlers.RenderAudio = function(req)
    if not res_app then return { error = "Resolve API object not available" } end
    local pm = res_app:GetProjectManager()
    local proj = pm and pm:GetCurrentProject()
    if not proj then return { error = "No project open" } end

    local export_path = req.export_path or ""
    local unique_id = req.unique_id or "badwords_render"
    local tl_name = req.timeline_name
    local track_indices = req.track_indices

    local current_tl = proj:GetCurrentTimeline()
    if tl_name and tl_name ~= "" and current_tl:GetName() ~= tl_name then
        local count = proj:GetTimelineCount() or 0
        for i = 1, count do
            local t = proj:GetTimelineByIndex(i)
            if t and t:GetName() == tl_name then
                proj:SetCurrentTimeline(t)
                current_tl = t
                break
            end
        end
    end

    -- Configure Render Settings for WAV Audio
    proj:DeleteAllRenderJobs()
    proj:SetCurrentRenderFormatAndCodec("wav", "LinearPCM")
    proj:SetRenderSettings({
        TargetDir = export_path,
        CustomName = unique_id,
        ExportAudio = true,
        ExportVideo = false
    })

    local job_id = proj:AddRenderJob()
    if not job_id or job_id == "" then
        return { error = "Failed to add render job" }
    end

    proj:StartRendering(job_id)

    -- Wait for completion
    while true do
        bmd.wait(0.25)
        local status = proj:GetRenderJobStatus(job_id)
        if status then
            local s_job = status.JobStatus or status.Status or ""
            if s_job == "Complete" then
                break
            elseif s_job == "Cancelled" or s_job == "Failed" then
                return { error = "Render job " .. s_job }
            end
        else
            break
        end
    end

    local final_file = export_path .. sep .. unique_id .. ".wav"
    return { ok = true, file_path = final_file }
end

handlers.ExportTimelineDrt = function(req)
    if not res_app then return { error = "Resolve API object not available" } end
    local pm = res_app:GetProjectManager()
    local proj = pm and pm:GetCurrentProject()
    if not proj then return { error = "No project open" } end

    local tl = proj:GetCurrentTimeline()
    if req and req.timeline_name and req.timeline_name ~= "" then
        local count = proj:GetTimelineCount() or 0
        for i = 1, count do
            local t = proj:GetTimelineByIndex(i)
            if t and t:GetName() == req.timeline_name then
                tl = t
                break
            end
        end
    end

    if not tl then return { error = "Timeline not found" } end
    local out_path = req and req.output_path
    if not out_path or out_path == "" then return { error = "output_path missing" } end

    local export_type = res_app.EXPORT_DRT or 1
    local ok = tl:Export(out_path, export_type)
    local start_f = 0
    pcall(function() start_f = tl:GetStartFrame() or 0 end)
    return { ok = (ok == true or ok == 1), start_frame = start_f }
end

handlers.ExportTimelineXml = function(req)
    if not res_app then return { error = "Resolve API object not available" } end
    local pm = res_app:GetProjectManager()
    local proj = pm and pm:GetCurrentProject()
    if not proj then return { error = "No project open" } end

    local tl = proj:GetCurrentTimeline()
    if req and req.timeline_name and req.timeline_name ~= "" then
        local count = proj:GetTimelineCount() or 0
        for i = 1, count do
            local t = proj:GetTimelineByIndex(i)
            if t and t:GetName() == req.timeline_name then
                tl = t
                break
            end
        end
    end

    if not tl then return { error = "Timeline not found" } end
    local out_path = req and req.output_path
    if not out_path or out_path == "" then return { error = "output_path missing" } end

    -- Export FCP XML (constant is 3 in DaVinci Resolve)
    local export_type = res_app.EXPORT_FCP_7_XML or 3
    local ok = tl:Export(out_path, export_type)
    return { ok = (ok == true or ok == 1) }
end

local function do_import_timeline_file(file_path, timeline_name)
    if not res_app then return { error = "Resolve API object not available" } end
    local pm = res_app:GetProjectManager()
    local proj = pm and pm:GetCurrentProject()
    if not proj then return { error = "No project open" } end

    local mp = proj:GetMediaPool()
    if not mp then return { error = "MediaPool not available" } end

    if not file_path or file_path == "" then return { error = "file_path missing" } end

    -- Reset to root folder before import
    pcall(function()
        local rf = mp:GetRootFolder()
        if rf then mp:SetCurrentFolder(rf) end
    end)

    local import_options = nil
    if timeline_name and timeline_name ~= "" then
        import_options = {
            timelineName = timeline_name,
            importSourceClips = true
        }
    end

    local imported = nil
    if import_options then
        local ok, res = pcall(function() return mp:ImportTimelineFromFile(file_path, import_options) end)
        if ok and res then imported = res end
    end
    if not imported then
        local ok, res = pcall(function() return mp:ImportTimelineFromFile(file_path) end)
        if ok and res then imported = res end
    end

    local imported_name = ""
    if imported then
        pcall(function() imported_name = imported:GetName() or "" end)
        if timeline_name and timeline_name ~= "" and imported_name ~= timeline_name then
            pcall(function()
                imported:SetName(timeline_name)
                imported_name = imported:GetName() or timeline_name
            end)
        end

        -- Move imported timeline into BadWords folder
        pcall(function()
            local root = mp:GetRootFolder()
            if not root then return end
            local sub_folders = root:GetSubFolderList() or {}
            local bw_folder = nil
            for _, f in ipairs(sub_folders) do
                if f:GetName() == "BadWords" then
                    bw_folder = f
                    break
                end
            end
            if not bw_folder then
                bw_folder = mp:AddSubFolder(root, "BadWords")
            end
            if bw_folder then
                local clips = root:GetClipList() or {}
                for _, c in ipairs(clips) do
                    if c:GetName() == imported_name then
                        mp:MoveClips({c}, bw_folder)
                        break
                    end
                end
            end
        end)
    end

    return { ok = (imported ~= nil), timeline_name = imported_name }
end

handlers.ImportTimelineDrt = function(req)
    local p = req and (req.drt_path or req.file_path or req.xml_path)
    local name = req and req.timeline_name
    return do_import_timeline_file(p, name)
end

handlers.ImportTimelineXml = function(req)
    local p = req and (req.xml_path or req.file_path or req.drt_path)
    local name = req and req.timeline_name
    return do_import_timeline_file(p, name)
end

handlers.ImportTimeline = function(req)
    local p = req and (req.file_path or req.drt_path or req.xml_path)
    local name = req and req.timeline_name
    return do_import_timeline_file(p, name)
end

handlers.JumpToSeconds = function(req)
    if not res_app then return { error = "Resolve API object not available" } end
    local secs = req and req.seconds or 0
    pcall(function() res_app:OpenPage("edit") end)

    local pm = res_app:GetProjectManager()
    local proj = pm and pm:GetCurrentProject()
    local tl = proj and proj:GetCurrentTimeline()
    if not tl then return { error = "No timeline active" } end

    local fps = tonumber(tl:GetSetting("timelineFrameRate")) or 24.0
    local start_f = tonumber(tl:GetStartFrame()) or 0
    local target_f = start_f + floor(secs * fps + 0.5)

    -- Convert frames to timecode hh:mm:ss:ff
    local total_sec = floor(target_f / fps)
    local f = target_f % floor(fps)
    local s = total_sec % 60
    local total_m = floor(total_sec / 60)
    local m = total_m % 60
    local h = floor(total_m / 60)
    local tc = string.format("%02d:%02d:%02d:%02d", h, m, s, f)

    pcall(function() tl:SetCurrentTimecode(tc) end)
    return { ok = true, timecode = tc }
end

handlers.ReapplyClipColors = function(req)
    if not res_app then return { error = "Resolve API object not available" } end
    local pm = res_app:GetProjectManager()
    local proj = pm and pm:GetCurrentProject()
    local tl = proj and proj:GetCurrentTimeline()
    if not tl then return { error = "No timeline active" } end

    local schedule = req and req.color_schedule or {}
    local sched_by_start = {}
    for _, item in ipairs(schedule) do
        if item.start_frame and item.color then
            sched_by_start[tostring(item.start_frame)] = item.color
        end
    end

    local function apply_to_tracks(track_type)
        local count = tl:GetTrackCount(track_type) or 0
        for tr = 1, count do
            local items = tl:GetItemListInTrack(track_type, tr)
            if items then
                for _, clip in ipairs(items) do
                    local sf = tostring(clip:GetStart())
                    if sched_by_start[sf] then
                        pcall(function() clip:SetClipColor(sched_by_start[sf]) end)
                    end
                end
            end
        end
    end

    apply_to_tracks("video")
    apply_to_tracks("audio")

    return { ok = true }
end

handlers.Exit = function()
    return { ok = true, message = "Bridge shutting down" }, { quit = true }
end

-- ---------------------------------------------------------------------------
-- 6. Main Server Loop
-- ---------------------------------------------------------------------------
print("=======================================================")
print("[BadWords] Starting BadWords Bridge...")
print("[BadWords] Mailbox directory: " .. tostring(mailbox_dir))
print("[BadWords] Platform: " .. tostring(platform))
print("[BadWords] Bridge ready. Waiting for BadWords desktop app...")
print("=======================================================")

local quitServer = false
local last_request_id = ""

while not quitServer do
    bmd.wait(0.1)

    if bmd.fileexists(request_file) then
        local chunk = loadfile(request_file)
        local ok, req = false, nil
        if chunk then
            ok, req = pcall(chunk)
        end

        if ok and type(req) == "table" and type(req.id) == "string" then
            if req.id == last_request_id then
                -- Request has already been processed; wait for client to delete request_file
                bmd.wait(0.2)
            else
                last_request_id = req.id
                bridge_ack(req.id)

                local data = json.decode(req.body)
                local result = nil
                local control = nil

                if data and data.func then
                    local handler = handlers[data.func]
                    if handler then
                        local h_ok, h_res, h_ctrl = pcall(handler, data)
                        if h_ok then
                            result = h_res or { ok = true }
                            control = h_ctrl
                        else
                            result = { error = tostring(h_res) }
                            print("[BadWords Bridge] Handler error: " .. tostring(h_res))
                        end
                    else
                        result = { error = "Unknown function: " .. tostring(data.func) }
                    end
                else
                    result = { error = "Invalid request JSON" }
                end

                bridge_respond(req.id, result)

                if control and control.quit then
                    quitServer = true
                end
            end
        end
    end
end

print("[BadWords] Bridge exited cleanly.")
