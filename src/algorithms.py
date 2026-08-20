#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: algorithms.py
ROLE: Core Module
DESCRIPTION:
Implements core alignment algorithms (Script vs Transcript Alignment).
"""

import re
import difflib
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from osdoc import log_info

# ==========================================
# CONSTANTS & CONFIG
# ==========================================

STOP_WORDS = {"a", "an", "the", "in", "on", "at", "to", "of", "i", "you", "he", "she", "it", "we", "they", "is", "are", "and", "or"}

# Fuzzy Thresholds
THRESH_LONG = 0.80   # Strict enough to prevent false positives for long words
THRESH_MID = 0.75    # Strict enough for medium words
THRESH_SHORT = 0.70  # Very strict for short words to prevent 'init' matching '.net'
# 0. HALLUCINATION SANITIZER (STAGE 9)
# ==========================================

def sanitize_hallucinations(transcript_words):
    """
    STAGE 9: Removes technical hallucination loops from raw Whisper output.
    A hallucination run is defined as: the same word repeating > 3 times
    consecutively AND each occurrence lasting < 0.2 seconds (suspiciously fast).
    Action: keep the first 2 instances, drop the rest, log a warning.
    """
    if not transcript_words:
        return transcript_words

    cleaned = []
    i = 0
    total_dropped = 0

    while i < len(transcript_words):
        w = transcript_words[i]
        raw_text = re.sub(r'[^\w]', '', w.get('text', '')).lower()

        # Count identical consecutive words
        run_count = 1
        while (i + run_count < len(transcript_words)):
            cand_text = re.sub(r'[^\w]', '', transcript_words[i + run_count].get('text', '')).lower()
            if cand_text == raw_text:
                run_count += 1
            else:
                break

        if run_count > 3:
            # Hallucination criterion: all words in the run are suspiciously short (< 0.2 s)
            all_short = all(
                (transcript_words[i + k].get('end', 0) - transcript_words[i + k].get('start', 0)) < 0.2
                for k in range(run_count)
            )
            if all_short:
                # Keep the first 2 instances, drop the rest
                cleaned.extend(transcript_words[i:i + 2])
                dropped = run_count - 2
                total_dropped += dropped
                i += run_count
                continue

        # Normal path: keep the word and advance
        cleaned.append(w)
        i += 1

    if total_dropped > 0:
        log_info(f"Sanitizer removed {total_dropped} hallucinated words.")

    return cleaned


# ==========================================
# 1. FILE HANDLING (Helpers)
# ==========================================

def read_docx_text(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        text_parts = []
        for elem in tree.iter():
            if elem.tag.endswith('}t'):
                if elem.text:
                    text_parts.append(elem.text)
        
        full_text = "\n".join(text_parts)
        # PATCH v6.6: Aggressive whitespace normalization
        # Replaces newlines, tabs, and multiple spaces with a single space.
        return re.sub(r'\s+', ' ', full_text).strip()
    except Exception as e:
        return f"[Error reading .docx] {e}"

def read_pdf_text(path):
    try:
        import pypdf # type: ignore
        reader = pypdf.PdfReader(path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + " " # Use space instead of newline to avoid joining words
        
        # PATCH v6.6: Aggressive whitespace normalization for PDFs
        # PDFs often have weird line breaks that break tokenization.
        return re.sub(r'\s+', ' ', text).strip()
    except ImportError:
        return "[Error] pypdf library missing."
    except Exception as e:
        return f"[Error reading PDF] {e}"

# ==========================================
# 2. PREPROCESSING & TOKENIZATION v5.0
# ==========================================

def super_clean(text):
    """
    Funkcja pomocnicza 'SuperCompare' (część A).
    Usuwa WSZYSTKO co nie jest cyfrą lub literą (włączając unicode).
    Zamienia słowne liczby 0-10 na cyfry.
    Mapuje znaki specjalne na słowa, żeby wyrównać skróty typu CTRL+K.
    """
    if not text: return ""
    text = str(text).lower()
    
    # Map common spoken symbols to words before stripping
    symbol_map = {
        '+': 'plus',
        '-': 'minus',
        '=': 'equals',
        '@': 'at',
        '#': 'hash',
        '*': 'star',
        '&': 'and',
        '%': 'percent'
    }
    for sym, word in symbol_map.items():
        text = text.replace(sym, word)
        
    cleaned = re.sub(r'[^\w]', '', text).replace('_', '')
    NUMBER_WORDS = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4', 
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
        'jeden': '1', 'dwa': '2', 'trzy': '3', 'cztery': '4', 
        'pięć': '5', 'piec': '5', 'sześć': '6', 'szesc': '6', 'siedem': '7', 
        'osiem': '8', 'dziewięć': '9', 'dziewiec': '9', 'dziesięć': '10', 'dziesiec': '10'
    }
    return NUMBER_WORDS.get(cleaned, cleaned)

def tokenize_v5(text):
    """
    Tokenizacja v5.0:
    1. Lowercase.
    2. Split po białych znakach.
    3. Strip interpunkcji KOŃCZĄCEJ/ZACZYNAJĄCEJ (.,?!:;), ale ZACHOWANIE wewnętrznej (192.168.0.1, wi-fi, don't).
    """
    if not text: return []
    
    # Pre-clean excessive whitespace to be safe
    text = re.sub(r'\s+', ' ', text)
    
    raw_tokens = text.lower().split()
    clean_tokens = []
    
    for t in raw_tokens:
        # Usuń interpunkcję z krawędzi słowa
        stripped = t.strip(".,?!:;\"'()[]{}")
        if stripped:
            clean_tokens.append(stripped)
            
    return clean_tokens

# ==========================================
# 3. FUZZY LOGIC & PHONETICS
# ==========================================

def simplified_metaphone(word):
    """Poor Man's Metaphone implementation."""
    if not word: return ""
    s = word.lower()
    s = re.sub(r'[bfpv]', '1', s)
    s = re.sub(r'[cgjkqsxz]', '2', s)
    s = re.sub(r'[dt]', '3', s)
    s = re.sub(r'l', '4', s)
    s = re.sub(r'[mn]', '5', s)
    s = re.sub(r'r', '6', s)
    if len(s) > 1:
        s = s[0] + re.sub(r'[aeiouy]', '', s[1:])
    s = re.sub(r'(.)\1+', r'\1', s)
    return s

def calculate_similarity(s1, s2):
    # FIX IN-07: quick_ratio() jest 3-5x szybsze, a wystarcza do progowania fuzzy matchingu
    return difflib.SequenceMatcher(None, s1, s2).quick_ratio()

def check_fuzzy_match(s1, s2):
    """
    Weryfikacja tekstowa na podstawie wersji 'super_clean' (wg specyfikacji v5.0).
    """
    c1 = super_clean(s1)
    c2 = super_clean(s2)
    
    if not c1 or not c2: return False
    
    sim = calculate_similarity(c1, c2)
    length = max(len(c1), len(c2))
    min_length = min(len(c1), len(c2))
    
    # v7.5 Anti-Cascade: Prevent absurd matches like "are" vs "a"
    if length > 0 and (min_length / length) < 0.4:
        return False
    
    threshold = THRESH_LONG
    if length < 4: threshold = THRESH_SHORT
    elif length <= 7: threshold = THRESH_MID
    
    if sim >= threshold:
        return True
        
    # Fonetyka dla niepewnych
    if sim >= 0.50:
        ph1 = simplified_metaphone(c1)
        ph2 = simplified_metaphone(c2)
        if ph1 and ph2 and ph1 == ph2:
            return True
            
    return False

# ==========================================
# 4. MAIN ALGORITHM CLASS (v5.0)
# ==========================================

class AnalysisResult(list):
    """
    PATCH v6.4: Klasa hybrydowa - Lista z atrybutami.
    Zachowuje się jak lista słów (dla engine.py),
    ale przechowuje missing_indices (dla gui.py).
    Rozwiązuje problem 'zamrożenia' (crashu wątku) przez niezgodność typów.
    """
    def __init__(self, iterable=None):
        super().__init__(iterable if iterable else [])
        self.missing_indices = []

class CompareEngineBase:
    def __init__(self, script_text, words_data, algo_settings=None):
        # --- Stage 6A: Unpack algorithm tuning parameters with safe defaults ---
        _s = algo_settings or {}
        self.algo_settings = _s  # Save original settings dictionary for conditional phases
        
        # fuzzy_threshold is stored as 0-100 in settings; normalize to 0.0-1.0
        self.fuzzy_thresh     = _s.get('algo_fuzzy_threshold', 80) / 100.0
        self.retake_lookahead = int(_s.get('algo_retake_lookahead', 80))
        self.distance_penalty = float(_s.get('algo_distance_penalty', 2.0))  # reserved for future use
        self.anchor_depth     = int(_s.get('algo_anchor_depth', 3))           # reserved for future use

        self.words_data = words_data
        self._sanitize_numbers()

        # A. Przygotowanie danych
        self.script_tokens = tokenize_v5(script_text)
        
        # Mapa Skryptu (Global Indexing)
        self.script_map = defaultdict(list)
        for idx, word in enumerate(self.script_tokens):
            self.script_map[word].append(idx)
        
        # Filtrowanie transkryptu (Z OMIJANIEM HALUCYNACJI)
        self.trans_tokens = []
        self.trans_indices = [] 
        
        for idx, w in enumerate(self.words_data):
            # v9.6 FULL CLEANUP: Reset all algorithm statuses before any processing.
            # This prevents unmatched gaps from retaining 'repeat' status from previous standalone runs,
            # which caused chain-reaction false positives in F.2b.
            w['status'] = w.get('manual_status')
            w['selected'] = bool(w['status'])
            w['is_auto'] = False
            w['is_retake'] = False
            w['algo_status'] = None

            if w.get('type') == 'silence' or w.get('is_inaudible') or w.get('_is_hallucination'):
                continue
            
            # W transkrypcie Whisper daje czyste słowa, ale upewnijmy się
            clean = w['text'].strip(".,?!:;\"'()[]{}").lower()
            if clean:
                self.trans_tokens.append(clean)
                self.trans_indices.append(idx)
        
        self.s_len = len(self.script_tokens)
        self.t_len = len(self.trans_tokens)
        
        # Mapa Historii (Gdzie skrypt[k] wystąpił w transkrypcie?)
        # Klucz: Script Index (k), Wartość: Transcript Index (j)
        self.history_map = {} 
        
        # PATCH v5.8: Strict Trace Map
        # Rejestr wszystkich dopasowań: TraceMap[index_transkryptu] = index_skryptu
        self.trace_map = {}
        
        # PATCH v6.3: List to track missing script parts for Yellow highlighting
        self.missing_script_indices = []

    def _sanitize_numbers(self):
        """
        STAGE 10: Merges decimal numbers that Whisper split into two/three tokens.
        Example: `0` and `.5` becomes `0.5`.
        This prevents false-positive Retake (Red) or Typo (Green) flags.
        """
        if not self.words_data:
            return

        cleaned = []
        i = 0

        while i < len(self.words_data):
            w = self.words_data[i]
            
            t1 = w.get('text', '').strip()
            c1 = super_clean(t1)
            
            if c1 and c1.isdigit() and i + 1 < len(self.words_data):
                next_w = self.words_data[i + 1]
                t2 = next_w.get('text', '').strip()
                c2 = super_clean(t2)
                
                # Case 1: `0` and `.5` (or `.5.`)
                if c2 and c2.isdigit() and len(t2) > 0 and t2[0] in '.,':
                    merged = w.copy()
                    merged['text'] = t1 + t2
                    merged['end'] = next_w.get('end', w.get('end'))
                    cleaned.append(merged)
                    i += 2
                    continue
                    
                # Case 3: `0.` and `5`
                if c2 and c2.isdigit() and len(t1) > 0 and t1[-1] in '.,':
                    merged = w.copy()
                    merged['text'] = t1 + t2
                    merged['end'] = next_w.get('end', w.get('end'))
                    cleaned.append(merged)
                    i += 2
                    continue
                
                # Case 2: `0` and `.` and `5`
                if not c2 and len(t2) > 0 and t2[0] in '.,' and i + 2 < len(self.words_data):
                    next_next_w = self.words_data[i + 2]
                    t3 = next_next_w.get('text', '').strip()
                    c3 = super_clean(t3)
                    if c3 and c3.isdigit():
                        merged = w.copy()
                        merged['text'] = t1 + t2 + t3
                        merged['end'] = next_next_w.get('end', w.get('end'))
                        cleaned.append(merged)
                        i += 3
                        continue
                    
            cleaned.append(w)
            i += 1

        self.words_data[:] = cleaned

    def mark_range(self, t_start_idx, t_end_idx, status, is_auto=False):
        """Oznacza zakres w words_data (indeksy wirtualne -> rzeczywiste)."""
        for k in range(t_start_idx, t_end_idx + 1):
            if k >= self.t_len: break
            real_idx = self.trans_indices[k]
            w = self.words_data[real_idx]
            
            # Reset
            w['status'] = None
            w['selected'] = False
            w['is_auto'] = False
            w['manual_status'] = None  # Reset manual override on fresh analysis
            w['algo_status'] = None    # Reset algo memory
            
            if status != 'normal':
                w['status'] = status
                w['selected'] = True
                w['is_auto'] = is_auto
                
                # NEW: Save algo origin for overlay reload logic
                if is_auto:
                    w['algo_status'] = status

    def _add_trace(self, t_idx, s_idx):
        """
        PATCH v6.0: ANCHOR SECURITY.
        Dodaje do mapy TYLKO jeśli dopasowanie jest częścią sekwencji.
        Eliminuje 'Blue Ocean' spowodowany przypadkowymi pojedynczymi trafieniami.
        """
        # Sprawdzenie wsteczne (Continuity)
        # Czy poprzednie słowo w transkrypcie (t-1) pasowało do poprzedniego słowa w skrypcie (s-1)?
        prev_match = (self.trace_map.get(t_idx - 1) == s_idx - 1)
        
        # Sprawdzenie w przód (Lookahead)
        # Czy następne słowo (t+1) pasuje do następnego słowa skryptu (s+1)?
        next_match = False
        if t_idx + 1 < self.t_len and s_idx + 1 < self.s_len:
            if self.super_compare(self.script_tokens[s_idx+1], self.trans_tokens[t_idx+1]):
                next_match = True
        
        # Dodajemy tylko, jeśli mamy kontekst (sąsiada)
        if prev_match or next_match:
            self.trace_map[t_idx] = s_idx

    def super_compare(self, s1, s2):
        """Funkcja pomocnicza B: SuperCompare."""
        return super_clean(s1) == super_clean(s2)

    def _fuzzy_match(self, s1, s2):
        """
        Stage 6A: Instance-level fuzzy match that uses self.fuzzy_thresh
        (derived from algo_fuzzy_threshold setting, normalized 0-1).
        Keeps phonetic fallback from module-level check_fuzzy_match.
        """
        c1 = super_clean(s1)
        c2 = super_clean(s2)
        if not c1 or not c2:
            return False
        sim = calculate_similarity(c1, c2)
        length = max(len(c1), len(c2))
        min_length = min(len(c1), len(c2))
        
        # v7.5 Anti-Cascade: Prevent absurd matches like "are" vs "a"
        if length > 0 and (min_length / length) < 0.4:
            return False
        # Scale short/mid thresholds relative to the user's long threshold
        thresh = self.fuzzy_thresh
        if length < 4:   thresh = min(thresh, THRESH_SHORT)
        elif length <= 7: thresh = min(thresh, THRESH_MID)
        if sim >= thresh:
            return True
        # Phonetic fallback
        if sim >= 0.50:
            ph1 = simplified_metaphone(c1)
            ph2 = simplified_metaphone(c2)
            if ph1 and ph2 and ph1 == ph2:
                return True
        return False

    def get_numeric_sequence_val(self, tokens, start_idx):
        """
        Pomocnik do Kroku 0. Zwraca ciąg samych cyfr oraz ile tokenów zużył.
        """
        buffer = ""
        count = 0
        limit = min(len(tokens), start_idx + 10) 
        for k in range(start_idx, limit):
            word = tokens[k]
            has_digit = any(c.isdigit() for c in word)
            if not has_digit: break
            digits = "".join(filter(str.isdigit, word))
            buffer += digits
            count += 1
        return buffer, count

    def _phase_d_smart_fragment_fill(self):
        """
        PATCH v5.8: Smart Fragment Fill.
        Analizuje TraceMap, ale liczy GRUPY (Smart Occurrence Counting),
        aby nie traktować pociętych liczb (IP, telefony) jako powtórzeń.
        """
        if not self.trace_map:
            return

        occurrences = defaultdict(list)
        
        for t_idx, s_idx in self.trace_map.items():
            occurrences[s_idx].append(t_idx)

        sorted_script_indices = sorted(occurrences.keys())

        log_info(f"[Phase D] Analyzing {len(sorted_script_indices)} unique script words...")

        count_retakes = 0
        
        for s_idx in sorted_script_indices:
            times = occurrences[s_idx]
            
            # Musi być co najmniej 2 punkty, żeby w ogóle myśleć o powtórzeniu
            if len(times) < 2:
                continue

            # Sortujemy indeksy transkryptu
            times.sort()
            
            # --- SMART COUNTING LOGIC ---
            # Liczymy ile jest ROZŁĄCZNYCH grup.
            groups = 0
            if times:
                groups = 1 # Pierwsza liczba zawsze zaczyna grupę
                for k in range(1, len(times)):
                    # Jeśli obecny indeks NIE jest następnikiem poprzedniego, to nowa grupa
                    if times[k] != times[k-1] + 1:
                        groups += 1
            
            # Warunek RETAKE: Muszą być przynajmniej 2 grupy podejść
            if groups < 2:
                # To prawdopodobnie pocięta liczba/nazwa (np. IP address)
                continue
            
            # --- LOCAL FLOOD FILL ---
            # v7.4 Anti Blue-Ocean Shield: Do not flood-fill absurdly large gaps.
            # If the span between the first take and the second take is huge,
            # it's a mapping error or a false positive retake on a stop word.
            local_start = times[0]
            local_end = times[-1]
            
            if local_end - local_start > 50:
                log_info(f"[Phase D] Skipping massive gap {local_end - local_start} words to prevent Blue Ocean.")
                continue
                
            # v7.6 FIX: Removed self.mark_range(local_start, local_end, 'repeat') here.
            # Phase C (Retake Logic) already colors the gaps properly. 
            # Phase D was aggressively over-coloring the final "keeper" take!
            count_retakes += 1

        log_info(f"--- PHASE D COMPLETED. Detected {count_retakes} genuine retake groups (Coloring handled by Phase C). ---")


# ==========================================
# 5. PUBLIC API (Adapter)
# ==========================================

def apply_debug_rgb_pattern(words_data):
    """
    Debug Mode: Colors entire transcript in Red-Green-Blue cycle.
    Used to test timestamp alignment and timeline cut precision.
    
    Pattern:
    - RED (bad)
    - GREEN (typo)
    - BLUE (repeat)
    """
    pattern = ['bad', 'typo', 'repeat']
    cycle_idx = 0
    
    log_info("[DEBUG] Applying RGB Pattern to all words...")
    
    for w in words_data:
        # Skip functional blocks
        if w.get('type') in ['silence', 'inaudible']:
            continue
            
        # Select status based on cycle
        status = pattern[cycle_idx % 3]
        
        w['status'] = status
        w['selected'] = True
        w['manual_status'] = status # Force persistence
        w['is_auto'] = False
        
        cycle_idx += 1
        
    result = AnalysisResult(words_data)
    result.missing_indices = [] # No missing script in debug mode
    return result


class CompareEngine(CompareEngineBase):
    def __init__(self, script_text, words_data, algo_settings=None):
        super().__init__(script_text, words_data, algo_settings)

    def _phase_e_fill_dp_gaps(self, match_pairs):
        """
        PATCH v6.3: DP Gap Filler with Fuzzy Split Word Detection.
        """
        if not match_pairs:
            return

        match_pairs.sort(key=lambda x: x[0])
        missing_set = set(self.missing_script_indices)
        
        def fill_gap(start_t, end_t, start_s, end_s):
            t_g = end_t - start_t - 1
            s_g = end_s - start_s - 1
            
            if t_g < 0 or s_g < 0:
                return
                
            if t_g > 0 and s_g > 0:
                # Be more lenient with typo grouping for split words. Whisper often splits 1 technical word into 3-4 words.
                if max(t_g, s_g) <= 8 or (abs(t_g - s_g) <= 4 and max(t_g, s_g) <= 12):
                    for t_idx in range(start_t + 1, end_t):
                        self.mark_range(t_idx, t_idx, 'typo', is_auto=True)
                    for s_idx in range(start_s + 1, end_s):
                        if s_idx in missing_set:
                            missing_set.remove(s_idx)
                return

            if s_g == 0 and 0 < t_g <= 6:
                gap_audio_words = [super_clean(self.trans_tokens[idx]) for idx in range(start_t + 1, end_t)]
                gap_str = "".join(gap_audio_words)
                
                prev_s_str = super_clean(self.script_tokens[start_s]) if start_s >= 0 else ""
                next_s_str = super_clean(self.script_tokens[end_s]) if end_s < self.s_len else ""
                
                prev_t_str = super_clean(self.trans_tokens[start_t]) if start_t >= 0 else ""
                next_t_str = super_clean(self.trans_tokens[end_t]) if end_t < self.t_len else ""
                
                # Check fuzzy equality
                def is_match(combined, target):
                    if not combined or not target: return False
                    if combined in target or target in combined: return True
                    return check_fuzzy_match(combined, target)
                
                if next_s_str and (is_match(gap_str, next_s_str) or is_match(gap_str + next_t_str, next_s_str) or is_match(next_t_str + gap_str, next_s_str)):
                    for t_idx in range(start_t + 1, end_t):
                        self.mark_range(t_idx, t_idx, 'typo', is_auto=True)
                    self.mark_range(end_t, end_t, 'typo', is_auto=True)
                    return
                    
                if prev_s_str and (is_match(gap_str, prev_s_str) or is_match(prev_t_str + gap_str, prev_s_str) or is_match(gap_str + prev_t_str, prev_s_str)):
                    for t_idx in range(start_t + 1, end_t):
                        self.mark_range(t_idx, t_idx, 'typo', is_auto=True)
                    self.mark_range(start_t, start_t, 'typo', is_auto=True)
                    return
                    
                if "plus" in gap_str and ("ctrl" in prev_s_str or "shift" in prev_s_str or "alt" in prev_s_str):
                    for t_idx in range(start_t + 1, end_t):
                        self.mark_range(t_idx, t_idx, 'typo', is_auto=True)
                    return

    def run(self):
        import time
        log_info(f"--- STARTING DP ALIGNMENT V6 (Script: {self.s_len}, Trans: {self.t_len}) ---")
        
        for j in range(self.t_len):
            self.mark_range(j, j, 'bad', is_auto=True)
            
        if self.s_len == 0 or self.t_len == 0:
            result = AnalysisResult(self.words_data)
            result.missing_indices = self.missing_script_indices
            return result

        # 1. Prepare normalized arrays
        s_norm = [super_clean(w) for w in self.script_tokens]
        t_norm = [super_clean(w) for w in self.trans_tokens]

        s_rev = s_norm[::-1]
        t_rev = t_norm[::-1]
        
        S = self.s_len
        T = self.t_len
        
        dp = [[0.0] * (T + 1) for _ in range(S + 1)]
        ptr = [[0] * (T + 1) for _ in range(S + 1)]
        
        for i in range(1, S + 1):
            dp[i][0] = -5.0 * i
            ptr[i][0] = 3
        for j in range(1, T + 1):
            dp[0][j] = -1.0 * j
            ptr[0][j] = 2
            
        # Pre-compute fuzzy memoization to avoid millions of calls
        fuzzy_memo = {}
        def check_fuzzy(w1, w2):
            if not w1 or not w2: return False
            key = (w1, w2)
            if key in fuzzy_memo: return fuzzy_memo[key]
            
            sim = calculate_similarity(w1, w2)
            length = max(len(w1), len(w2))
            min_length = min(len(w1), len(w2))
            if length > 0 and (min_length / length) < 0.4:
                fuzzy_memo[key] = False
                return False
                
            thresh = self.fuzzy_thresh
            if length < 4: thresh = min(thresh, THRESH_SHORT)
            elif length <= 7: thresh = min(thresh, THRESH_MID)
            
            if sim >= thresh:
                fuzzy_memo[key] = True
                return True
                
            if sim >= 0.50:
                ph1 = simplified_metaphone(w1)
                ph2 = simplified_metaphone(w2)
                if ph1 and ph2 and ph1 == ph2:
                    fuzzy_memo[key] = True
                    return True
                    
            fuzzy_memo[key] = False
            return False

        # We pre-calculate lengths and first/last characters to avoid string operations in the inner loop
        s_cache = []
        for i in range(1, S + 1):
            w = s_rev[i-1]
            s_cache.append((w, len(w), w[0] if w else '', w[-1:] if w else ''))
            
        t_cache = []
        for j in range(1, T + 1):
            w = t_rev[j-1]
            t_cache.append((w, len(w), w[0] if w else '', w[-1:] if w else ''))

        # Band initialization (Sakoe-Chiba Band style)
        # Using a generously wide dynamic band reduces iterations by 80-95% for long texts
        # while mathematically guaranteeing we won't lose precision on any realistic alignment.
        BAND_RADIUS = max(400, int(T * 0.2))
        
        # Initialize with extremely low penalty outside the evaluated band
        dp = [[-999999.0] * (T + 1) for _ in range(S + 1)]
        ptr = [[0] * (T + 1) for _ in range(S + 1)]
        
        dp[0][0] = 0.0
        for i in range(1, S + 1):
            dp[i][0] = -5.0 * i
            ptr[i][0] = 3
        for j in range(1, T + 1):
            dp[0][j] = -1.0 * j
            ptr[0][j] = 2

        for i in range(1, S + 1):
            s_word, s_len, s_first, s_last = s_cache[i-1]
            
            # Calculate band window
            j_center = int(i * T / max(1, S))
            j_start = max(1, j_center - BAND_RADIUS)
            j_end = min(T, j_center + BAND_RADIUS)
            
            for j in range(j_start, j_end + 1):
                t_word, t_len, t_first, t_last = t_cache[j-1]
                
                is_exact = False
                is_fuzzy = False
                best_k_exact = 0
                best_k_fuzzy = 0
                best_s_exact = 0
                best_s_fuzzy = 0
                
                base_is_fuzzy = False
                if s_word == t_word and s_word != "":
                    is_exact = True
                else:
                    if s_len > 3 and len(t_word) > 3 and t_word in s_word:
                        is_fuzzy = True
                        base_is_fuzzy = True
                    elif check_fuzzy(s_word, t_word):
                        is_fuzzy = True
                        base_is_fuzzy = True
                        
                    # Only block fuzzy combo matches if base is fuzzy. Exact combos should always be allowed.
                    if s_word != "" and t_len < s_len and s_len > 3:
                        if t_first == s_first or t_last == s_last or (len(t_word) > 3 and t_word in s_word):
                            combo = t_word
                            for k in range(1, 12):
                                if j - 1 - k >= 0:
                                    combo = combo + t_rev[j - 1 - k]
                                    if len(combo) > s_len + 5:
                                        break
                                    if s_word == combo:
                                        is_exact = True
                                        best_k_exact = k
                                        break
                                    elif not base_is_fuzzy and check_fuzzy(s_word, combo):
                                        is_fuzzy = True
                                        best_k_fuzzy = k

                    if not is_exact and t_word != "" and s_len < t_len and t_len > 3:
                        if s_first == t_first or s_last == t_last or (len(s_word) > 3 and s_word in t_word):
                            combo_s = s_word
                            for k in range(1, 12):
                                if i - 1 - k >= 0:
                                    combo_s = combo_s + s_rev[i - 1 - k]
                                    if len(combo_s) > t_len + 5:
                                        break
                                    if combo_s == t_word:
                                        is_exact = True
                                        best_s_exact = k
                                        break
                                    elif not base_is_fuzzy and check_fuzzy(combo_s, t_word):
                                        is_fuzzy = True
                                        best_s_fuzzy = k

                # v11.0: Contiguity and Recency Bonuses
                # 1. Recency tie-breaker: slightly prefer matches near the end of the transcript (small j).
                # This mathematically guarantees we ALWAYS pick the final take.
                recency_bonus = (T - j) * 0.005 
                
                if is_exact:
                    walk_i = i - 1 - best_s_exact
                    walk_j = j - 1 - best_k_exact
                    while walk_i > 0 and ptr[walk_i][walk_j] == 3:
                        walk_i -= 1
                    prev_ptr = ptr[walk_i][walk_j]
                    contiguity = 15.0 if prev_ptr >= 10 else 0.0
                    score_exact = dp[i-1-best_s_exact][j-1-best_k_exact] + 10.0 + contiguity + recency_bonus + (best_k_exact * 2.0) + (best_s_exact * 2.0)
                else:
                    score_exact = -999999.0
                    
                if is_fuzzy:
                    walk_i = i - 1 - best_s_fuzzy
                    walk_j = j - 1 - best_k_fuzzy
                    while walk_i > 0 and ptr[walk_i][walk_j] == 3:
                        walk_i -= 1
                    prev_ptr = ptr[walk_i][walk_j]
                    contiguity = 15.0 if prev_ptr >= 10 else 0.0
                    score_fuzzy = dp[i-1-best_s_fuzzy][j-1-best_k_fuzzy] + 5.0 + contiguity + recency_bonus + (best_k_fuzzy * 5.0) + (best_s_fuzzy * 5.0)
                else:
                    score_fuzzy = -999999.0

                score_skip_t = dp[i][j-1] - 0.5
                score_skip_s = dp[i-1][j] - 2.0
                
                # Fast path for non-matching case (happens ~95% of time)
                if score_exact == -999999.0 and score_fuzzy == -999999.0:
                    if score_skip_t >= score_skip_s:
                        dp[i][j] = score_skip_t
                        ptr[i][j] = 2
                    else:
                        dp[i][j] = score_skip_s
                        ptr[i][j] = 3
                    continue
                
                # Slower path if we have a match
                best_score = score_exact
                if is_exact and best_s_exact > 0:
                    best_ptr = 30 + best_s_exact
                elif is_exact:
                    best_ptr = 10 + best_k_exact
                else:
                    best_ptr = 0
                    
                if score_fuzzy > best_score:
                    best_score = score_fuzzy
                    if best_s_fuzzy > 0:
                        best_ptr = 40 + best_s_fuzzy
                    else:
                        best_ptr = 20 + best_k_fuzzy
                    
                if score_skip_t >= best_score:
                    best_score = score_skip_t
                    best_ptr = 2
                    
                if score_skip_s > best_score:
                    best_score = score_skip_s
                    best_ptr = 3
                    
                dp[i][j] = best_score
                ptr[i][j] = best_ptr

        self.dp = dp
        self.ptr = ptr
        i = S
        j = T
        match_pairs = []
        
        while i > 0 or j > 0:
            if i == 0:
                j -= 1
                continue
            if j == 0:
                actual_s = S - i
                self.missing_script_indices.append(actual_s)
                i -= 1
                continue
                
            p = ptr[i][j]
            if p == 0 or p == 1:
                actual_s = S - i
                actual_t = T - j
                match_pairs.append((actual_t, actual_s, p))
                i -= 1
                j -= 1
            elif p >= 10 and p < 20:
                k = p - 10
                actual_s = S - i
                for step in range(k + 1):
                    actual_t = T - (j - step)
                    match_pairs.append((actual_t, actual_s, 0))
                i -= 1
                j -= (k + 1)
            elif p >= 20 and p < 30:
                k = p - 20
                actual_s = S - i
                for step in range(k + 1):
                    actual_t = T - (j - step)
                    match_pairs.append((actual_t, actual_s, 1))
                i -= 1
                j -= (k + 1)
            elif p >= 30 and p < 40:
                k = p - 30
                actual_t = T - j
                for step in range(k + 1):
                    actual_s = S - (i - step)
                    match_pairs.append((actual_t, actual_s, 0))
                i -= (k + 1)
                j -= 1
            elif p >= 40:
                k = p - 40
                actual_t = T - j
                for step in range(k + 1):
                    actual_s = S - (i - step)
                    match_pairs.append((actual_t, actual_s, 1))
                i -= (k + 1)
                j -= 1
            elif p == 2:
                j -= 1
            elif p == 3:
                actual_s = S - i
                self.missing_script_indices.append(actual_s)
                i -= 1

        for t_idx, s_idx, p in match_pairs:
            if p == 0:
                self.mark_range(t_idx, t_idx, 'normal')
            else:
                self.mark_range(t_idx, t_idx, 'typo', is_auto=True)
            self._add_trace(t_idx, s_idx)
            
        self.match_pairs = match_pairs
        
        self.missing_script_indices.sort()
        self._phase_d_smart_fragment_fill()
        self._phase_e_fill_dp_gaps(match_pairs)
        self._phase_f_retake_detection(match_pairs)
        self._phase_h_smooth_statuses(match_pairs)
        
        # Export DP exact coordinates to words_data for SBS (must happen BEFORE Phase G which shrinks the array)
        for t_idx, s_idx, p in match_pairs:
            if 0 <= t_idx < self.t_len:
                real_t_idx = self.trans_indices[t_idx]
                if 0 <= real_t_idx < len(self.words_data):
                    self.words_data[real_t_idx]['_dp_script_index'] = s_idx

        if self.algo_settings and self.algo_settings.get('run_phase_g', False):
            self._phase_g_merge_combos(match_pairs)

        end_time = time.time()
        result = AnalysisResult(self.words_data)
        result.missing_indices = self.missing_script_indices
        return result

    def _phase_f_retake_detection(self, match_pairs):
        """
        PHASE F: Post-DP cleanup & retake detection.
        
        Four passes:
        F.1 — Retake detection with bidirectional comparison & gap merging.
        F.2 — Single-word red suppression.
        F.3 — Split-word grouping (typo↔bad adjacency fix).
        F.4 — Two-word red suppression (catch remaining short false positives).
        """
        if not match_pairs or self.t_len == 0:
            return

        # ── F.1: RETAKE DETECTION ──────────────────────────────────────────
        matched_t_indices = set()
        for t_idx, s_idx, p in match_pairs:
            matched_t_indices.add(t_idx)
        for k in range(self.t_len):
            real_idx = self.trans_indices[k]
            w = self.words_data[real_idx]
            if w.get('status') in (None, 'normal', 'typo'):
                matched_t_indices.add(k)

        # Collect raw gaps
        raw_gaps = []  # list of (gap_indices, good_before_indices, good_after_indices)
        current_gap = []
        for k in range(self.t_len):
            if k not in matched_t_indices:
                current_gap.append(k)
            else:
                if current_gap:
                    # Collect previous good block (up to 25 words, walk backwards)
                    good_before = []
                    for j in range(current_gap[0] - 1, max(current_gap[0] - 26, -1), -1):
                        if j >= 0 and j in matched_t_indices:
                            good_before.append(j)
                        else:
                            break
                    good_before.reverse()
                    
                    # Collect next good block (up to 25 words, skip small gaps)
                    good_after = []
                    skip_budget = 3  # allow skipping up to 3 non-matched words
                    for j in range(k, min(k + 40, self.t_len)):
                        if j in matched_t_indices:
                            good_after.append(j)
                            if len(good_after) >= 25:
                                break
                        else:
                            skip_budget -= 1
                            if skip_budget < 0:
                                break
                    raw_gaps.append((current_gap[:], good_before, good_after))
                    current_gap = []
        if current_gap:
            good_before = []
            for j in range(current_gap[0] - 1, max(current_gap[0] - 26, -1), -1):
                if j >= 0 and j in matched_t_indices:
                    good_before.append(j)
                else:
                    break
            good_before.reverse()
            raw_gaps.append((current_gap[:], good_before, []))

        # ── v8.1: SMART GAP MERGING ──────────────────────────────────────
        # When the DP alignment "punctures" a retake by matching a single
        # word in the middle (e.g. "underlay" or "w"), it splits what should
        # be one retake into multiple tiny gaps. Merge adjacent gaps that
        # are separated by ≤3 "bridge" words into a single combined gap.
        merged_gaps = []
        i = 0
        while i < len(raw_gaps):
            gap_indices, good_before, good_after = raw_gaps[i]
            
            # Try to merge with subsequent gaps
            while i + 1 < len(raw_gaps):
                next_gap_indices, _, next_good_after = raw_gaps[i + 1]
                
                # How many matched words between this gap's end and next gap's start?
                if gap_indices and next_gap_indices:
                    bridge_size = next_gap_indices[0] - gap_indices[-1] - 1
                    if bridge_size <= 3:
                        # Absorb bridge words and next gap into current gap
                        bridge = list(range(gap_indices[-1] + 1, next_gap_indices[0]))
                        gap_indices = gap_indices + bridge + next_gap_indices
                        good_after = next_good_after
                        i += 1
                        continue
                break
            
            merged_gaps.append((gap_indices, good_before, good_after))
            i += 1

        # v8.1 MULTILINGUAL STOP WORDS
        # These words appear so frequently in any language that they cannot
        # serve as evidence of a retake. Extended with common Polish, German,
        # Spanish, French, and other European language stop words.
        STOP_SET = {
            # English
            'the', 'it', 'and', 'to', 'you', 'is', 'a', 'an', 'in', 'on',
            'at', 'of', 'or', 'we', 'they', 'are', 'but', 'for', 'this',
            'that', 'with', 'have', 'has', 'do', 'was', 'be', 'so', 'if',
            'not', 'just', 'its', 'i', 'my', 'he', 'she', 'our', 'your',
            'can', 'will', 'then', 'than', 'from', 'by', 'as', 'im',
            'dont', 'what', 'how', 'when', 'where', 'all', 'no', 'yes',
            # Polish
            'w', 'i', 'na', 'z', 'do', 'o', 'nie', 'to', 'się', 'sie',
            'je', 'jak', 'co', 'po', 'za', 'od', 'ze', 'jest', 'ale',
            'ten', 'ta', 'te', 'ich', 'go', 'tam', 'tu', 'już', 'juz',
            'tak', 'też', 'tez', 'czy', 'bo', 'mi', 'nam', 'was',
            # German
            'der', 'die', 'das', 'ein', 'und', 'ist', 'ich', 'du', 'er',
            'wir', 'sie', 'es', 'mit', 'auf', 'fur', 'von', 'zu', 'den',
            'dem', 'des', 'im', 'am', 'um', 'als', 'aus', 'bei',
            # French
            'le', 'la', 'les', 'un', 'une', 'et', 'est', 'de', 'du',
            'en', 'il', 'je', 'ce', 'ne', 'pas', 'que', 'qui', 'sur',
            # Spanish
            'el', 'la', 'los', 'las', 'un', 'una', 'es', 'en', 'de',
            'por', 'con', 'no', 'se', 'lo', 'que', 'del', 'y', 'a', 'su',
            'para', 'al', 'como', 'más', 'o', 'pero', 'sus', 'le', 'me', 'si',
            # Italian
            'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'di', 'a', 
            'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'e', 'o', 'ma', 'se', 
            'che', 'non', 'mi', 'ti', 'ci', 'vi', 'si', 'del', 'al', 'dal', 'nel',
            # Portuguese
            'o', 'a', 'os', 'as', 'um', 'uma', 'e', 'do', 'da', 'dos', 'das', 
            'de', 'em', 'no', 'na', 'nos', 'nas', 'por', 'com', 'para', 'se', 
            'não', 'me', 'te', 'lhe', 'vos', 'que', 'ao', 'aos', 'pelo', 'pela',
            # Dutch
            'de', 'het', 'een', 'en', 'van', 'in', 'te', 'dat', 'die', 'is', 
            'voor', 'met', 'op', 'zijn', 'niet', 'aan', 'er', 'ook', 'als', 
            'om', 'dan', 'of', 'uit', 'door', 'over', 'maar',
            # Russian
            'и', 'в', 'не', 'на', 'я', 'быть', 'с', 'он', 'что', 'а', 'по', 
            'это', 'она', 'этот', 'к', 'но', 'они', 'мы', 'как', 'из', 'у', 
            'который', 'то', 'за', 'свой', 'весь', 'год', 'от', 'так', 'о', 
            'для', 'ты', 'же', 'все', 'тот', 'мочь', 'вы', 'его',
            # Japanese
            'は', 'が', 'に', 'を', 'で', 'て', 'と', 'から', 'まで', 'より', 'も', 'の', 'です', 'ます', 'する', 'した',
            # Chinese
            '的', '了', '和', '是', '就', '都', '而', '及', '与', '着', '或', '一个', '没有', '我们', '你们', '他们', '她', '他', '它', '在', '也', '有',
            # Korean
            '은', '는', '이', '가', '에', '에서', '를', '을', '의', '로', '으로', '과', '와', '도', '고', '다', '입니다', '합니다',
            # Arabic
            'في', 'من', 'على', 'إلى', 'أن', 'عن', 'مع', 'هذا', 'التي', 'كان', 'لا', 'ما', 'أو', 'هذه', 'بعد', 'بين', 'هو', 'كل', 'وقد', 'كانت'
        }
        
        FWD_OVERLAP_THRESHOLD = 0.55   # v8.0: raised from 0.35 — need >50% content word overlap
        BWD_OVERLAP_THRESHOLD = 0.65   # v8.0: raised from 0.55

        def get_words_from_indices(indices):
            """Extract cleaned words from transcript indices."""
            words = []
            for idx in indices:
                if 0 <= idx < self.t_len:
                    cleaned = super_clean(self.trans_tokens[idx])
                    if cleaned:
                        words.append(cleaned)
            return words

        def content_overlap_ratio(gap_words, ref_words):
            """Calculate overlap EXCLUDING stop words. Returns (ratio, matched_content_count).
            
            Only non-stop-word matches count as evidence of a retake.
            The ratio is computed over content words only."""
            if not gap_words or not ref_words:
                return 0.0, 0
            
            ref_set = set(ref_words)
            matched_content = 0
            total_content = 0
            
            for gw in set(gap_words):
                if len(gw) <= 1:
                    continue
                if gw in STOP_SET:
                    continue  # stop words don't count as evidence
                total_content += 1
                if gw in ref_set:
                    matched_content += 1
                else:
                    for rw in ref_set:
                        if len(rw) <= 1 or rw in STOP_SET:
                            continue
                        if check_fuzzy_match(gw, rw):
                            matched_content += 1
                            break
            
            ratio = matched_content / max(1, total_content)
            return ratio, matched_content

        def prefix_match_count(gap_words, ref_words):
            """Count prefix matches (first N identical/fuzzy words)."""
            pm = 0
            for i in range(min(len(gap_words), len(ref_words))):
                if gap_words[i] == ref_words[i] or check_fuzzy_match(gap_words[i], ref_words[i]):
                    pm += 1
                else:
                    break
            return pm

        for gap_indices, good_before_idx, good_after_idx in merged_gaps:
            if not gap_indices:
                continue

            gap_words = get_words_from_indices(gap_indices)
            content_gap = [w for w in gap_words if len(w) > 1 and w not in STOP_SET]
            if not content_gap:
                continue  # gap is all stop words — can't determine retake

            good_after_words = get_words_from_indices(good_after_idx)
            good_before_words = get_words_from_indices(good_before_idx)

            is_retake = False
            
            # Forward comparison (gap vs next good block) — primary signal
            # This is the core retake check: does the gap repeat what comes next?
            if good_after_words:
                fwd_ratio, fwd_matched = content_overlap_ratio(gap_words, good_after_words)
                fwd_prefix = prefix_match_count(gap_words, good_after_words)
                unique_content = len(set(content_gap))
                
                # Strong evidence: high content-word overlap
                if fwd_ratio >= FWD_OVERLAP_THRESHOLD and fwd_matched >= 2:
                    is_retake = True
                # Very strong evidence: 3+ word prefix match (speaker restarted sentence)
                if fwd_prefix >= 3:
                    is_retake = True
                # Medium gaps with 2-word prefix: speaker started the same way
                if fwd_prefix >= 2 and unique_content <= 6:
                    is_retake = True
                # Very short gaps (1-2 unique content words): single content word match
                if unique_content <= 2 and fwd_matched >= 1:
                    is_retake = True
                
                # Subsequence detection: the gap may START with filler/false-start
                # but END with a repeat of the after block. Scan the gap for a
                # trailing window that overlaps strongly with the after block's start.
                if not is_retake and len(gap_words) >= 4:
                    after_content = [w for w in good_after_words if len(w) > 1 and w not in STOP_SET]
                    if after_content:
                        for start_pos in range(len(gap_words) - 2):
                            tail = gap_words[start_pos:]
                            tail_prefix = prefix_match_count(tail, good_after_words)
                            if tail_prefix >= 2:
                                is_retake = True
                                break
                            tail_content = [w for w in tail if len(w) > 1 and w not in STOP_SET]
                            if len(tail_content) >= 2:
                                tail_ratio, tail_matched = content_overlap_ratio(tail, good_after_words)
                                if tail_ratio >= 0.60 and tail_matched >= 2:
                                    # Enforce that the identified retake start actually relates to the next block
                                    tail_first_matches = tail[0] in good_after_words or any(len(rw) > 1 and check_fuzzy_match(tail[0], rw) for rw in good_after_words)
                                    if tail_first_matches:
                                        is_retake = True
                                        break

            # Backward comparison (gap vs previous good block) — even stricter
            # Only for longer gaps (4+ content words) to avoid false positives
            if not is_retake and good_before_words and len(content_gap) >= 4:
                bwd_ratio, bwd_matched = content_overlap_ratio(gap_words, good_before_words)
                bwd_prefix = prefix_match_count(gap_words, good_before_words)
                if bwd_ratio >= BWD_OVERLAP_THRESHOLD and bwd_matched >= 4:
                    is_retake = True
                if bwd_prefix >= 4:
                    is_retake = True

            # v8.0: Script comparison REMOVED.
            # The old logic compared gap words against ALL script tokens.
            # Since the transcript IS someone reading the script, nearly every
            # gap matched the script at 50%+, causing everything to become retake.
            # True retakes are caught by forward/backward comparison above.

            if is_retake:
                for idx in gap_indices:
                    if 0 <= idx < self.t_len:
                        self.mark_range(idx, idx, 'repeat')
                        real_idx = self.trans_indices[idx]
                        self.words_data[real_idx]['is_retake'] = True

        # ── F.2: SINGLE-WORD SUPPRESSION ─────────────────────────────────────
        # Suppress isolated single 'bad' or 'repeat' words surrounded by
        # normal content. Single-word gaps are almost always false positives.
        # Also check temporal distance: if neighbor is >3s away, it's a
        # separate speech segment and shouldn't count as a "neighbor".
        for k in range(self.t_len):
            real_idx = self.trans_indices[k]
            w = self.words_data[real_idx]
            
            if w.get('status') == 'repeat':
                pass
            elif w.get('status') == 'bad':
                import re
                text_len = len(re.sub(r'[^\w]', '', w.get('text', '')))
                if text_len > 3 or w.get('is_filler'):
                    continue
            else:
                continue
            
            cur_time = w.get('start', 0) or 0
            prev_marked = False
            next_marked = False
            if k > 0:
                prev_real = self.trans_indices[k - 1]
                prev_w = self.words_data[prev_real]
                if prev_w.get('status') in ('bad', 'repeat'):
                    prev_time = prev_w.get('start', 0) or 0
                    if abs(cur_time - prev_time) < 3.0:
                        prev_marked = True
            if k < self.t_len - 1:
                next_real = self.trans_indices[k + 1]
                next_w = self.words_data[next_real]
                if next_w.get('status') in ('bad', 'repeat'):
                    next_time = next_w.get('start', 0) or 0
                    if abs(next_time - cur_time) < 3.0:
                        next_marked = True
            
            if not prev_marked and not next_marked:
                w['status'] = None
                w['selected'] = False
                w['is_auto'] = False
                w['algo_status'] = None
                w['is_retake'] = False

        # F.2b (Typo->Repeat Promotion) was removed because it aggressively bled blue color into valid green/red segments.
        # F.4 was removed because it aggressively suppressed valid 2-word errors.

    def _phase_h_smooth_statuses(self, match_pairs):
        """
        Phase H: Semantic Status Cleanup.
        Evaluates blocks of 'repeat' tokens. If a block has NO fuzzy match
        with the nearby script window, it is a non-relevant filler and should
        be downgraded to 'bad'.
        """
        import re, difflib
        real_idx_to_s = {self.trans_indices[t]: s for t, s, p in match_pairs}
        words = self.words_data

        i = 0
        while i < len(words):
            w = words[i]
            if w.get('status') == 'repeat' and w.get('type') != 'silence':
                start = i
                while i < len(words) and words[i].get('status') == 'repeat':
                    i += 1
                end = i
                
                # Find nearest matched script index to constrain the search window
                nearest_s = -1
                for fw in range(end, len(words)):
                    if fw in real_idx_to_s:
                        nearest_s = real_idx_to_s[fw]
                        break
                if nearest_s == -1:
                    for bw in range(start - 1, -1, -1):
                        if bw in real_idx_to_s:
                            nearest_s = real_idx_to_s[bw]
                            break
                if nearest_s == -1: 
                    nearest_s = 0
                
                s_start = max(0, nearest_s - 15)
                s_end = min(len(self.script_tokens), nearest_s + 15)
                
                import re, difflib
                window_text = " ".join(self.script_tokens[s_start:s_end]).lower()
                window_text = re.sub(r'[^\w\s]', '', window_text)
                
                block_text = " ".join([self.words_data[j].get('text', '') for j in range(start, end)]).lower()
                block_text = re.sub(r'[^\w\s]', '', block_text)
                
                has_match = False
                
                # Check 1: Fuzzy block match (for things like "...icious." matching "resolution")
                if block_text and window_text:
                    sm = difflib.SequenceMatcher(None, block_text, window_text)
                    match = sm.find_longest_match(0, len(block_text), 0, len(window_text))
                    coverage = match.size / len(block_text) if len(block_text) > 0 else 0
                    if coverage > 0.3 or match.size >= 5:
                        has_match = True
                
                # Check 2: Exact word match (for things like "So," matching "So")
                if not has_match:
                    window_words = set(window_text.split())
                    for bw in block_text.split():
                        if len(bw) >= 2 and bw in window_words:
                            has_match = True
                            break
                            
                if not has_match:
                    for j in range(start, end):
                        if self.words_data[j].get('type') != 'silence':
                            self.words_data[j]['status'] = 'bad'
                            self.words_data[j]['algo_status'] = 'bad'
                            self.words_data[j]['selected'] = True
            else:
                i += 1

    def _phase_g_merge_combos(self, match_pairs):
        """
        Groups transcript words that were mapped to the exact same script word 
        (via split-word combo lookahead) and merges them into a single word 
        in self.words_data to clean up the UI presentation.
        """
        from collections import defaultdict
        s_to_t = defaultdict(list)
        for t_idx, s_idx, p in match_pairs:
            s_to_t[s_idx].append(t_idx)
            
        merge_groups = []
        for s_idx, t_indices in s_to_t.items():
            if not t_indices:
                continue
            t_indices.sort()
            
            # Check contiguity for merging
            is_contiguous = True
            for i in range(1, len(t_indices)):
                if t_indices[i] != t_indices[i-1] + 1:
                    is_contiguous = False
                    break
                    
            if is_contiguous:
                merge_groups.append((s_idx, t_indices))
                    
        # Sort groups in reverse order so merging doesn't affect earlier indices
        merge_groups.sort(key=lambda x: x[1][0], reverse=True)
        
        for s_idx, t_indices in merge_groups:
            real_indices = [self.trans_indices[t] for t in t_indices]
            first_real = real_indices[0]
            last_real = real_indices[-1]
            
            merged = self.words_data[first_real].copy()
            
            # Combine the text if multiple words
            if len(t_indices) > 1:
                combo_text = ""
                for r in real_indices:
                    w_text = self.words_data[r].get('text', '')
                    if combo_text and not w_text.startswith(" ") and not w_text.startswith("-"):
                        combo_text += " " + w_text
                    else:
                        combo_text += w_text
                merged['text'] = combo_text
            else:
                combo_text = merged.get('text', '')
                
            if 'start' in self.words_data[first_real]:
                merged['start'] = self.words_data[first_real]['start']
            merged['end'] = self.words_data[last_real].get('end', self.words_data[last_real].get('start', 0.0))
            
            # --- Smart Auto-Correction Logic ---
            script_raw = self.script_tokens[s_idx]
            import re
            is_tech = bool(re.search(r'[/.\\+\-_@#*]|\b[a-zA-Z]+[0-9]+|[0-9]+[a-zA-Z]+', script_raw))
            script_digits = re.sub(r'\D', '', script_raw)
            combo_digits = re.sub(r'\D', '', combo_text)
            
            p_val = next((p for t, s, p in match_pairs if s == s_idx and t in t_indices), 1)
            
            should_autocorrect = False
            if p_val == 0 and len(t_indices) > 1:
                # Exact combo match. Safe to snap.
                should_autocorrect = True
            elif is_tech and p_val == 1:
                import difflib
                from algorithms import super_clean
                s_fp = super_clean(script_raw)
                c_fp = super_clean(combo_text)
                if s_fp and c_fp:
                    ratio = difflib.SequenceMatcher(None, s_fp, c_fp).ratio()
                    is_path = '/' in script_raw or '\\' in script_raw
                    if is_path:
                        if ratio >= 0.75:
                            should_autocorrect = True
                    else:
                        if ratio >= 0.80 and script_digits == combo_digits:
                            should_autocorrect = True
                            
            if should_autocorrect:
                merged['text'] = script_raw
                merged['status'] = None
                merged['is_auto'] = False
                merged['algo_status'] = None
            
            # Replace the group of words (or single word) with the processed word
            self.words_data[first_real:last_real+1] = [merged]


def compare_script_to_transcript(script_text, words_data, algo_settings=None):
    engine = CompareEngine(script_text, words_data, algo_settings=algo_settings)
    return engine.run()

def absorb_inaudible_into_repeats(words_data):
    """
    Scalanie luk 'inaudible' pomiędzy blokami 'repeat'.
    """
    n = len(words_data)
    if n < 3: return words_data
    
    target_status = 'repeat'
    
    # Helpers
    def get_prev_effective_index(start_i):
        idx = start_i - 1
        while idx >= 0:
            if words_data[idx].get('type') != 'silence': return idx
            idx -= 1
        return -1

    def get_next_effective_index(start_i):
        idx = start_i
        while idx < n:
            if words_data[idx].get('type') != 'silence': return idx
            idx += 1
        return -1

    i = 0
    while i < n:
        if words_data[i].get('type') == 'silence':
            i += 1
            continue

        if words_data[i].get('is_inaudible'):
            start_idx = i
            curr = i
            while curr < n:
                w = words_data[curr]
                if w.get('is_inaudible') or w.get('type') == 'silence': curr += 1
                else: break
            
            end_idx = curr
            left_idx = get_prev_effective_index(start_idx)
            prev_ok = (left_idx >= 0 and words_data[left_idx].get('status') == target_status)
            effective_right = get_next_effective_index(end_idx) if end_idx < n else -1
            next_ok = (effective_right != -1 and words_data[effective_right].get('status') == target_status)
            
            if prev_ok and next_ok:
                for k in range(start_idx, end_idx):
                    if words_data[k].get('is_inaudible'):
                        words_data[k]['status'] = 'repeat'
                        words_data[k]['selected'] = False
            i = end_idx
        else:
            i += 1
    return words_data

def _fuzzy_word_eq(a, b):
    """
    Standalone fuzzy equality for two cleaned words.
    Exact match OR 1-character tolerance for words >= 4 chars.
    Uses Levenshtein-like check via SequenceMatcher for speed.
    """
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    # Only allow fuzzy for words that are long enough to tolerate 1-char diff
    if max(la, lb) < 4:
        return False
    sim = difflib.SequenceMatcher(None, a, b).ratio()
    # For a 4-char word, 1 diff → ratio ~0.75; for 6-char → ~0.83
    # Threshold: 0.70 to allow exactly 1-char difference in 4+ char words
    return sim >= 0.70


def analyze_repeats(words_data, show_inaudible=True, algo_settings=None):
    """
    Standalone Human Error & Repeat Detector v4.0
    
    Detects human speech errors WITHOUT a reference script:
    1. Direct Stutters (1-word repeats)
    2. False Starts & Cut-offs (words ending in '-' or '...')
    3. Phrase Retakes (Dynamic gap-based n-gram matching)
    """
    if algo_settings is None:
        algo_settings = {}

    # 1. Smart Reset
    for w in words_data:
        if w.get('_is_hallucination') or w.get('type') in ['silence', 'inaudible'] or w.get('is_inaudible'):
            continue
        if w.get('status') == 'repeat':
            w['status'] = w.get('manual_status')
            w['selected'] = (w['status'] in ['bad', 'inaudible', 'typo'])
            w['is_auto'] = False

    # 2. Build flow with raw text preservation for punctuation analysis
    flow = []
    for idx, w in enumerate(words_data):
        if w.get('type') in ['silence', 'inaudible']:
            continue
        if w.get('is_inaudible'):
            continue
        if w.get('_is_hallucination'):
            continue
            
        raw_text = w['text'].strip()
        clean_text = re.sub(r'[^\w]', '', raw_text).lower()
        
        if not clean_text and not raw_text:
            continue
            
        flow.append({
            'real_idx': idx,
            'clean': clean_text,
            'raw': raw_text,
            'is_stop': clean_text in STOP_WORDS
        })

    n_flow = len(flow)
    marked_indices = set()

    # PASS 1: Micro-errors (Cut-offs, Partial Words, Direct Stutters)
    for i in range(n_flow):
        curr = flow[i]
        raw = curr['raw']
        clean = curr['clean']
        
        # A. Dash cutoffs (e.g., "archit-")
        if raw.endswith('-') and len(clean) > 0:
            marked_indices.add(i)
            
        # B. Ellipsis cutoffs (e.g., "Log... Look" or "te... touched")
        elif raw.endswith('...') and len(clean) > 0:
            # Check next 2 words to see if it's a restart (shares first letter)
            for j in range(1, 3):
                if i + j < n_flow:
                    next_clean = flow[i+j]['clean']
                    if len(next_clean) > 0 and clean[0] == next_clean[0]:
                        marked_indices.add(i)
                        break
                        
        # C. Direct 1-word stutters ("to to", "I I")
        if i + 1 < n_flow:
            next_clean = flow[i+1]['clean']
            if clean == next_clean and len(clean) > 0:
                marked_indices.add(i)
                marked_indices.add(i+1)

    # PASS 2: Phrase Retakes & False Starts (Dynamic Gap-based N-gram)
    LOOKAHEAD = int(algo_settings.get('algo_retake_lookahead', 60))
    
    for i in range(n_flow):
        # We don't want to start phrase matching on a pure cut-off word
        if flow[i]['raw'].endswith('-'):
            continue

        for j in range(i + 1, min(n_flow, i + LOOKAHEAD)):
            w_i_anchor = flow[i]['clean']
            w_j_anchor = flow[j]['clean']
            
            if not w_i_anchor or not w_j_anchor:
                continue
                
            # Anchor must match to even start comparing the phrase
            if w_i_anchor != w_j_anchor and not _fuzzy_word_eq(w_i_anchor, w_j_anchor):
                continue
                
            curr_i = i
            curr_j = j
            mismatches = 0
            best_i = i
            best_j = j
            
            # Expand match with tolerance for mismatched words inside the phrase
            while curr_i < j and curr_j < n_flow:
                w_i = flow[curr_i]['clean']
                w_j = flow[curr_j]['clean']
                
                if not w_i or not w_j:
                    break
                    
                if w_i == w_j or _fuzzy_word_eq(w_i, w_j):
                    curr_i += 1
                    curr_j += 1
                    best_i = curr_i
                    best_j = curr_j
                else:
                    matched_so_far = curr_i - i
                    max_allowed = 1 if matched_so_far < 4 else 2
                    
                    if mismatches >= max_allowed:
                        break
                        
                    recovered = False
                    if curr_i + 1 < j and curr_j + 1 < n_flow:
                        w_i1 = flow[curr_i+1]['clean']
                        w_j1 = flow[curr_j+1]['clean']
                        
                        # Substitution recovery
                        if w_i1 == w_j1 or _fuzzy_word_eq(w_i1, w_j1):
                            curr_i += 2
                            curr_j += 2
                            mismatches += 1
                            recovered = True
                            best_i = curr_i
                            best_j = curr_j
                        # Deletion in phrase 2
                        elif flow[curr_i]['clean'] == w_j1 or _fuzzy_word_eq(flow[curr_i]['clean'], w_j1):
                            curr_i += 1
                            curr_j += 2
                            mismatches += 1
                            recovered = True
                            best_i = curr_i
                            best_j = curr_j
                        # Deletion in phrase 1
                        elif w_i1 == flow[curr_j]['clean'] or _fuzzy_word_eq(w_i1, flow[curr_j]['clean']):
                            curr_i += 2
                            curr_j += 1
                            mismatches += 1
                            recovered = True
                            best_i = curr_i
                            best_j = curr_j
                            
                    if not recovered:
                        break
                        
            match_len_i = best_i - i
            match_len_j = best_j - j
            match_len = max(match_len_i, match_len_j)
            
            if match_len < 2:
                continue
                
            gap = max(0, j - best_i)
            content_count = sum(1 for k in range(match_len_i) if not flow[i+k]['is_stop'])
            has_long_word = any(len(flow[i+k]['clean']) >= 4 and not flow[i+k]['is_stop'] for k in range(match_len_i))
            
            is_retake = False
            
            if match_len == 2:
                # 2 words: Must be very close to be considered a retake
                if gap <= 2:
                    is_retake = True
                elif gap <= 4 and content_count >= 2 and has_long_word:
                    is_retake = True
            elif match_len == 3:
                if gap <= 4:
                    is_retake = True
                elif gap <= 8 and content_count >= 1:
                    is_retake = True
            elif match_len == 4:
                if gap <= 6:
                    is_retake = True
                elif gap <= 10 and content_count >= 1:
                    is_retake = True
            elif match_len >= 5:
                if gap <= 10:
                    is_retake = True
                elif content_count >= 2:
                    is_retake = True
                    
            if is_retake:
                for k in range(match_len_i):
                    marked_indices.add(i + k)
                for k in range(match_len_j):
                    marked_indices.add(j + k)

    # 3. Apply markings
    count = 0
    for fi in marked_indices:
        real_idx = flow[fi]['real_idx']
        w = words_data[real_idx]
        if w.get('manual_status') and w['manual_status'] != 'repeat':
            continue
        w['status'] = 'repeat'
        w['selected'] = False
        w['is_auto'] = True
        w['algo_status'] = 'repeat'
        count += 1

    log_info(f"[Standalone v4.1] Marked {count} words as human errors/repeats.")
    return words_data, count

# ==========================================
# 6. GUI LOGIC HELPERS (Decoupled Logic)
# ==========================================

def apply_auto_filler_logic(words_data, fillers, is_enabled):
    fillers_lower = [f.lower() for f in fillers]
    for w in words_data:
        clean_text = w.get('text', '').strip(".,?!:;\"'()[]{}").lower()
        if is_enabled and clean_text in fillers_lower:
            if not w.get('manual_status'): # Do not overwrite manual markings
                w['status'] = 'bad'
                w['is_auto'] = True
                w['selected'] = True
        else:
            # CLEANUP: If it was auto-marked previously, but no longer qualifies, clear it
            if w.get('is_auto'):
                w['status'] = w.get('manual_status')
                w['is_auto'] = False
                w['selected'] = bool(w['status'])
    return words_data

def propagate_status_change(words_data, target_id, new_status):
    """
    Calculates which words need status updates based on 'inaudible' grouping.
    Returns a list of tuples: (word_id, final_status).
    Also updates 'manual_status' to allow base-layer persistence.
    """
    updates = []
    
    if target_id < 0 or target_id >= len(words_data):
        return updates

    target_w = words_data[target_id]

    if target_w.get('is_inaudible'):
        # Expand selection to cover contiguous block of inaudible/silence
        start = target_id
        while start > 0:
            prev = words_data[start-1]
            if prev.get('is_inaudible') or prev.get('type') == 'silence':
                start -= 1
            else:
                break
        
        end = target_id
        while end < len(words_data)-1:
            nxt = words_data[end+1]
            if nxt.get('is_inaudible') or nxt.get('type') == 'silence':
                end += 1
            else:
                break
        
        for i in range(start, end + 1):
            w = words_data[i]
            if w.get('is_inaudible'):
                final_status = new_status
                
                # Apply in-place change. Removed the hardcoded fallback to 'inaudible'
                # to allow the eraser tool to properly clear the fragment base layer.
                w['status'] = final_status
                w['manual_status'] = final_status # Base layer
                w['is_auto'] = False # Remove auto flag
                
                w['selected'] = (final_status in ['bad', 'inaudible', 'typo', 'repeat'])
                updates.append((w['id'], final_status))
    else:
        # Standard word update
        w_obj = target_w
        
        w_obj['status'] = new_status
        w_obj['manual_status'] = new_status # Base layer
        w_obj['is_auto'] = False # Remove auto flag
        
        w_obj['selected'] = (new_status in ['bad', 'inaudible', 'typo', 'repeat'])
        updates.append((w_obj['id'], new_status))
        
    return updates

def calculate_script_missing_ranges(text_content, missing_indices):
    """
    Maps missing word indices to character ranges in the raw script text.
    Returns list of (start_index, end_index) tuples, where indices 
    are absolute character positions in the text.
    """
    if not missing_indices:
        return []

    tokens_map = []
    pattern = re.compile(r'\S+')
    matches = list(pattern.finditer(text_content))
    
    # Filter matches to build a valid token map (skipping pure punctuation if tokenizer did so)
    for m in matches:
        raw = m.group()
        # Same cleaning logic as in engine/algo to ensure index alignment
        clean = raw.strip(".,?!:;\"'()[]{}")
        if clean:
            tokens_map.append(m)

    ranges = []
    for idx in missing_indices:
        if idx < len(tokens_map):
            match = tokens_map[idx]
            ranges.append((match.start(), match.end()))
            
    return ranges


# ==========================================
# 7. SIDE-BY-SIDE SCRIPT / TRANSCRIPT VIEW
# ==========================================

def _script_lines_for_side_by_side(script_text):
    """
    Intelligently splits the script into logical sentences/rows.
    - Preserves double newlines (paragraphs).
    - Merges single newlines (hard wraps).
    - Splits paragraphs into sentences based on punctuation followed by a capital letter.
    - Ignores rows that contain no alphanumeric characters (e.g., just "..." or "-").
    """
    text = script_text.replace('\r\n', '\n')
    paragraphs = re.split(r'\n\s*\n', text)
    final_rows = []
    
    for para in paragraphs:
        # Collapse single newlines and multiple spaces within a paragraph
        para = re.sub(r'\s+', ' ', para).strip()
        if not para:
            continue
            
        # We find sentence boundaries: [.!?] (optionally followed by quotes/brackets)
        # then spaces, then an Uppercase letter or Number.
        # We insert a newline before the Uppercase letter to split it cleanly.
        # \1 captures the punctuation, \2 captures the Uppercase letter.
        para = re.sub(r'([.!?]+["\')\]]?)\s+([A-Z0-9ŚĆŻŹĄĘÓŁŃ])', r'\1\n\2', para)
        
        for sentence in para.split('\n'):
            sentence = sentence.strip()
            if not re.search(r'\w', sentence):
                continue
                
            # Sub-sentence Flow Breaker:
            # Subdivide extremely long sentences at logical pauses (,, ;, :, —, ...) 
            # while ensuring we don't over-fragment (each piece must have >= 5 words).
            chunks = re.split(r'([,;:—]+|\.{2,})\s+', sentence)
            
            sub_rows = []
            curr_str = ""
            curr_words = 0
            
            i = 0
            while i < len(chunks):
                text_part = chunks[i]
                punct_part = chunks[i+1] if i + 1 < len(chunks) else ""
                
                segment = text_part + punct_part
                seg_words = len(segment.split())
                
                if curr_words == 0:
                    curr_str = segment
                    curr_words = seg_words
                else:
                    if curr_words >= 12:
                        sub_rows.append(curr_str.strip())
                        curr_str = segment
                        curr_words = seg_words
                    else:
                        curr_str += " " + segment
                        curr_words += seg_words
                i += 2
                
            if curr_str:
                # Only merge backwards if the trailing thought is extremely short (< 3 words)
                if curr_words < 3 and len(sub_rows) > 0:
                    sub_rows[-1] += " " + curr_str.strip()
                else:
                    sub_rows.append(curr_str.strip())
                    
            for r in sub_rows:
                if re.search(r'\w', r):
                    final_rows.append(r)
                
    if not final_rows:
        return [script_text.strip()] if script_text.strip() else []
        
    return final_rows


def _tokens_from_script_lines(lines):
    tokens = []
    for row_idx, line in enumerate(lines):
        for match in re.finditer(r"\S+", line):
            raw = match.group(0)
            clean = super_clean(raw)
            if clean:
                tokens.append({"text": raw, "clean": clean, "row": row_idx})
    return tokens


def _tokens_from_words_data(words_data):
    tokens = []
    for w in words_data or []:
        if w.get("type") in ("silence", "inaudible") or w.get("is_inaudible"):
            continue
        clean = super_clean(w.get("text", ""))
        if clean:
            tokens.append({
                "text": w.get("text", "").strip(),
                "clean": clean,
                "status": w.get("status"),
                "word_id": w.get("id"),
                "is_segment_start": w.get("is_segment_start", False),
                "start": w.get("start", 0.0),
                "original_word": w,
            })
    return tokens


def _side_by_side_text_from_transcript_tokens(tokens):
    """
    Keeps detected retake runs visually separated. The GUI renders newline
    characters as a fresh line inside the transcript cell.
    """
    if not tokens:
        return ""

    parts = []
    prev_repeat = False
    for tok in tokens:
        is_repeat = tok.get("status") == "repeat"
        if is_repeat and parts and not prev_repeat:
            parts.append("\n")
        elif parts and parts[-1] != "\n":
            parts.append(" ")
        parts.append(tok.get("text", ""))
        prev_repeat = is_repeat
    return "".join(parts).strip()


def build_side_by_side_alignment(script_text, words_data):
    """
    Builds rows for the side-by-side compare view.
    
    Strategy: Group by SCRIPT LINES, not transcript segments.
    1. Split script into lines (user line-breaks, or sentence fallback).
    2. Map each transcript token to its exact script line using _dp_script_index from CompareEngine.
    3. Absorb repeat runs into the script line they're repeating.
    4. Unmatched transcript tokens (improv) → own row with empty script.
    5. Unmatched script lines (unspoken) → own row with empty transcript.
    """
    script_lines = _script_lines_for_side_by_side(script_text)
    trans_tokens = _tokens_from_words_data(words_data)

    if not script_lines and not trans_tokens:
        return []

    # Build flat script token list with line indices
    script_tokens = []
    for line_idx, line in enumerate(script_lines):
        for match in re.finditer(r"\S+", line):
            raw = match.group(0)
            clean = super_clean(raw)
            if clean:
                script_tokens.append({"text": raw, "clean": clean, "line": line_idx})

    if not script_tokens and not trans_tokens:
        return []

    # Map each transcript token → script line (or -1 for unmatched/improv)
    trans_line_map = [-1] * len(trans_tokens)

    for ti, t in enumerate(trans_tokens):
        orig_word = t.get("original_word", {})
        s_idx = orig_word.get("_dp_script_index")
        
        # We only trust the DP mapping if it's NOT a bad/repeat word.
        # Bad and repeat words should be anchored to their context via backward-fill.
        status = t.get("status")
        if s_idx is not None and 0 <= s_idx < len(script_tokens) and status not in ("bad", "repeat"):
            trans_line_map[ti] = script_tokens[s_idx]["line"]

    # Smart Inline Bad Logic: identify short 'bad' blocks to be absorbed inline
    for ti in range(len(trans_tokens)):
        trans_tokens[ti]['is_inline_bad'] = False
        
    bad_blocks = []
    current_block = []
    for ti in range(len(trans_tokens)):
        if trans_tokens[ti].get("status") == "bad":
            current_block.append(ti)
        else:
            if current_block:
                bad_blocks.append(current_block)
                current_block = []
    if current_block:
        bad_blocks.append(current_block)
        
    for block in bad_blocks:
        # If the bad block is short (up to 3 words), treat it as an inline error/stutter
        # rather than a full improvised paragraph, so it doesn't break the SBS layout.
        if len(block) <= 3:
            for ti in block:
                trans_tokens[ti]['is_inline_bad'] = True

    # Force 'bad' and 'repeat' words to -1, to isolate them and let backward-fill group retakes.
    for ti in range(len(trans_tokens)):
        status = trans_tokens[ti].get("status")
        if status in ("bad", "repeat"):
            trans_line_map[ti] = -1

    # Backward-fill MUST run first! 
    # In BadWords, false starts and retakes precede the final "good" matched take.
    # We want them to attach to the NEXT matched script line.
    last_matched_line = -1
    for ti in range(len(trans_tokens) - 1, -1, -1):
        tok = trans_tokens[ti]
        if tok.get("status") == "bad" and not tok.get("is_inline_bad"):
            continue
        if trans_line_map[ti] != -1:
            last_matched_line = trans_line_map[ti]
        elif (tok.get("status") == "repeat" or tok.get("is_inline_bad")) and last_matched_line != -1:
            trans_line_map[ti] = last_matched_line

    # Forward-fill: acts as a fallback for trailing repeats at the end of the 
    # recording, or edge cases where backward-fill couldn't find a match.
    last_matched_line = -1
    for ti in range(len(trans_tokens)):
        tok = trans_tokens[ti]
        if tok.get("status") == "bad" and not tok.get("is_inline_bad"):
            continue
        if trans_line_map[ti] != -1:
            last_matched_line = trans_line_map[ti]
        elif (tok.get("status") == "repeat" or tok.get("is_inline_bad")) and trans_line_map[ti] == -1 and last_matched_line != -1:
            trans_line_map[ti] = last_matched_line

    # Bridge-fill: absorb isolated unmatched tokens (bad/None) that sit between
    # two groups assigned to the SAME script line. This prevents small gaps 
    # (like a stutter or filler word mid-retake) from splitting a row.
    for ti in range(len(trans_tokens)):
        if trans_line_map[ti] != -1:
            continue
            
        tok_status = trans_tokens[ti].get("status")
        if tok_status == "bad" and not trans_tokens[ti].get("is_inline_bad"):
            continue
            
        # Look backward and forward for nearest assigned lines
        prev_line = -1
        for pi in range(ti - 1, -1, -1):
            if trans_line_map[pi] != -1:
                prev_line = trans_line_map[pi]
                break
        next_line = -1
        for ni in range(ti + 1, len(trans_tokens)):
            if trans_line_map[ni] != -1:
                next_line = trans_line_map[ni]
                break
                
        if prev_line != -1 and prev_line == next_line:
            trans_line_map[ti] = prev_line
        elif tok_status != "bad":
            if prev_line != -1:
                trans_line_map[ti] = prev_line
            elif next_line != -1:
                trans_line_map[ti] = next_line

    # Build line → transcript tokens mapping (ordered list of groups)
    # We need to preserve transcript ORDER, so we walk through trans_tokens
    # and emit groups: (line_idx_or_None, [tokens])
    groups = []  # list of (line_idx, [token, ...])
    current_line = None
    current_toks = []

    for ti, tok in enumerate(trans_tokens):
        line = trans_line_map[ti]
        if line == current_line:
            current_toks.append(tok)
        else:
            if current_toks:
                groups.append((current_line, current_toks))
            current_line = line
            current_toks = [tok]
    if current_toks:
        groups.append((current_line, current_toks))

    # Track which script lines have been used
    used_script_lines = set()
    for line_idx, _ in groups:
        if line_idx is not None and line_idx != -1:
            used_script_lines.add(line_idx)

    # Build final rows by interleaving script lines and transcript groups
    final_rows = []
    emitted_script_lines = set()

    # Walk through groups in transcript order
    for line_idx, toks in groups:
        # Before emitting this group, emit any earlier unmatched script lines
        if line_idx is not None and line_idx != -1:
            for sl in range(line_idx):
                if sl not in emitted_script_lines and sl not in used_script_lines:
                    final_rows.append({
                        "script_text": script_lines[sl],
                        "transcript_tokens": [],
                        "transcript_text": "",
                        "script_kind": "missing",
                        "transcript_kind": "missing_gap",
                    })
                    emitted_script_lines.add(sl)

        if line_idx is None or line_idx == -1:
            # Improvisation / unmatched transcript
            final_rows.append({
                "script_text": "",
                "transcript_tokens": toks,
                "transcript_text": " ".join(t.get("text", "") for t in toks),
                "script_kind": "improv_gap",
                "transcript_kind": "improv",
                "_is_interruption": True
            })
        else:
            is_interruption = False
            if line_idx in emitted_script_lines:
                # This script line was interrupted by an improvisation.
                # To maintain strict chronology, we create a new row but do not duplicate the script text.
                script_line_text = ""
                is_interruption = True
            else:
                script_line_text = script_lines[line_idx] if line_idx < len(script_lines) else ""
                emitted_script_lines.add(line_idx)
                
            final_rows.append({
                "_line_idx": line_idx,
                "script_text": script_line_text,
                "transcript_tokens": toks,
                "transcript_text": " ".join(t.get("text", "") for t in toks),
                "script_kind": "normal",
                "transcript_kind": "normal",
                "_is_interruption": is_interruption
            })

    # Append any remaining unmatched script lines at the end
    for sl in range(len(script_lines)):
        if sl not in emitted_script_lines:
            final_rows.append({
                "script_text": script_lines[sl],
                "transcript_tokens": [],
                "transcript_text": "",
                "script_kind": "missing",
                "transcript_kind": "missing_gap",
            })

    # Clean up internal keys
    for row in final_rows:
        row.pop("_line_idx", None)

    def is_clean_normal(r):
        if r.get("script_kind") != "normal":
            return False
        for t in r.get("transcript_tokens", []):
            if t.get("status") in ("bad", "repeat"):
                return False
        return True

    # Performance & UI fix: Merge consecutive "missing" rows into a single block.
    # We also merge consecutive "improv_gap" rows.
    # Most importantly, we merge consecutive "clean" normal rows (no red/blue errors)
    # into larger blocks to make error-filled lines stand out more visually.
    merged_rows = []
    for row in final_rows:
        if merged_rows and row["script_kind"] == "missing" and merged_rows[-1]["script_kind"] == "missing":
            merged_rows[-1]["script_text"] += "\n\n" + row["script_text"]
        elif merged_rows and row["script_kind"] == "improv_gap" and merged_rows[-1]["script_kind"] == "improv_gap":
            merged_rows[-1]["transcript_tokens"].extend(row["transcript_tokens"])
            if merged_rows[-1]["transcript_text"] and row["transcript_text"]:
                merged_rows[-1]["transcript_text"] += " " + row["transcript_text"]
            else:
                merged_rows[-1]["transcript_text"] += row["transcript_text"]
        elif merged_rows and is_clean_normal(row) and is_clean_normal(merged_rows[-1]):
            # Count how many script lines are already in the merged block
            sentence_count = merged_rows[-1]["script_text"].count("\n\n") + 1
            if sentence_count < 2:
                merged_rows[-1]["script_text"] += "\n\n" + row["script_text"]
                merged_rows[-1]["transcript_tokens"].extend(row["transcript_tokens"])
                if merged_rows[-1]["transcript_text"] and row["transcript_text"]:
                    merged_rows[-1]["transcript_text"] += " " + row["transcript_text"]
                else:
                    merged_rows[-1]["transcript_text"] += row["transcript_text"]
            else:
                merged_rows.append(row)
        else:
            merged_rows.append(row)

    return merged_rows
