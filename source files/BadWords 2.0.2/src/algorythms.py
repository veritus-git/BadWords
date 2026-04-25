#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: algorythms.py
ROLE: Tool Layer
DESCRIPTION:
CORE LOGIC v6.7 (COVERAGE VALIDATION) - Script vs Transcript Alignment.
Features:
- ANALYZE (COMPARE) v5.0 implementation
- SuperNormalization (SuperCompare) for robust matching
- Numeric Greed (Handling split numbers/IPs)
- Advanced Retake Detection (Fuzzy Anchor + Lookahead with noise skip)
- PATCH v5.8: NUMERIC PROTECTION & STRICT TRACE (Smart Grouping)
- PATCH v5.9: INSERTION PRIORITY (Fixes "any settings" issue)
- PATCH v6.0: ANCHOR SECURITY & DEEP YELLOW (Fixes Blue Ocean & Missing Sync)
- PATCH v6.1: FUZZY SKIP & TAIL CHECK (Fuzzy Deletion Lookahead & Trailing Missing)
- PATCH v6.3: YELLOW MISSING REPORT (Correctly captures internal & tail missing words)
- PATCH v6.4: ANTI-FREEZE HYBRID RETURN (Fixes 'infinite loop' caused by tuple return)
- PATCH v6.5: DISTANCE PENALTY (Fixes False Long-Distance Retake bugs)
- PATCH v6.6: HEAD SYNC & PDF NORMALIZATION (Fixes script start offset and messy PDF whitespaces)
- PATCH v6.7: COVERAGE VALIDATION (Ensures found words/retakes are not marked missing)
- DEBUG MODE: RGB Pattern Injection
- Handling of Deletions and Insertions
- Document readers (PDF/DOCX)
- [NEW] GUI Helpers (Logic extracted from presentation layer)
- [NEW] HALLUCINATION SHIELD: Algorithms explicitly ignore _is_hallucination tags to preserve them.
"""

import re
import difflib
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

# ==========================================
# CONSTANTS & CONFIG
# ==========================================

STOP_WORDS = {"a", "an", "the", "in", "on", "at", "to", "of", "i", "you", "he", "she", "it", "we", "they", "is", "are", "and", "or"}

# Fuzzy Thresholds
THRESH_SHORT = 0.50  # < 4 chars
THRESH_MID   = 0.65  # 4-7 chars
THRESH_LONG  = 0.75  # > 7 chars

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
    Usuwa WSZYSTKO co nie jest cyfrą lub literą (a-z, 0-9).
    """
    if not text: return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())

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
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def check_fuzzy_match(s1, s2):
    """
    Weryfikacja tekstowa na podstawie wersji 'super_clean' (wg specyfikacji v5.0).
    """
    c1 = super_clean(s1)
    c2 = super_clean(s2)
    
    if not c1 or not c2: return False
    
    sim = calculate_similarity(c1, c2)
    length = max(len(c1), len(c2))
    
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

class CompareEngineV5:
    def __init__(self, script_text, words_data):
        # A. Przygotowanie danych
        self.script_tokens = tokenize_v5(script_text)
        
        # Mapa Skryptu (Global Indexing)
        self.script_map = defaultdict(list)
        for idx, word in enumerate(self.script_tokens):
            self.script_map[word].append(idx)
        
        # Filtrowanie transkryptu (Z OMIJANIEM HALUCYNACJI)
        self.trans_tokens = []
        self.trans_indices = [] 
        
        for idx, w in enumerate(words_data):
            if w.get('type') == 'silence' or w.get('is_inaudible') or w.get('_is_hallucination'):
                continue
            
            # W transkrypcie Whisper daje czyste słowa, ale upewnijmy się
            clean = w['text'].strip(".,?!:;\"'()[]{}").lower()
            if clean:
                self.trans_tokens.append(clean)
                self.trans_indices.append(idx)
        
        self.words_data = words_data
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

    def run(self):
        i = 0 # Script index
        j = 0 # Trans index
        
        print(f"--- STARTING COMPARE v6.7 (Script: {self.s_len}, Trans: {self.t_len}) ---")

        # -------------------------------------------------
        # PHASE -1: HEAD SYNC (PATCH v6.6)
        # Fixes startup crash when script has a long title/intro not present in audio.
        # Finds where the transcript actually begins in the script.
        # -------------------------------------------------
        head_search_limit = min(self.s_len, 300) # Check first 300 words of script
        trans_sample_len = min(self.t_len, 5)   # Use first 5 words of transcript
        
        if head_search_limit > 0 and trans_sample_len >= 3:
            best_k = -1
            # Try to find the first 3 words of transcript in the beginning of script
            for k in range(head_search_limit):
                match_count = 0
                for m in range(3): # Check tri-gram
                    if k + m < self.s_len and m < self.t_len:
                        if self.super_compare(self.script_tokens[k+m], self.trans_tokens[m]):
                            match_count += 1
                        else:
                            break
                
                if match_count == 3: # Found a solid anchor of 3 words
                    best_k = k
                    break
            
            if best_k > 0:
                print(f"[Head Sync] Detected offset. Skipping first {best_k} script words (Title/Intro).")
                # Mark skipped words as missing
                for skipped in range(best_k):
                    self.missing_script_indices.append(skipped)
                i = best_k # Move script pointer to the actual start

        while i < self.s_len and j < self.t_len:
            s_word = self.script_tokens[i]
            t_word = self.trans_tokens[j]
            
            # -------------------------------------------------
            # KROK 0: AGRESYWNE LICZBY (NUMERIC GREED)
            # -------------------------------------------------
            if any(c.isdigit() for c in s_word):
                s_digits, s_count = self.get_numeric_sequence_val(self.script_tokens, i)
                t_digits, t_count = self.get_numeric_sequence_val(self.trans_tokens, j)
                
                if s_digits and t_digits and s_digits == t_digits:
                    # MATCH!
                    self.mark_range(j, j + t_count - 1, 'normal')
                    
                    # TraceMap Update for Numerics
                    # Liczby z natury są sekwencją cyfr, więc traktujemy je jako pewne
                    for offset in range(t_count):
                         self.trace_map[j + offset] = i 

                    # Historia (Legacy)
                    for offset in range(s_count):
                         if j + offset < j + t_count:
                             self.history_map[i + offset] = j + offset
                         else:
                             self.history_map[i + offset] = j + t_count - 1

                    i += s_count
                    j += t_count
                    continue
            
            # -------------------------------------------------
            # KROK 1: SUPER EXACT (SUPER NORMALIZATION)
            # -------------------------------------------------
            if self.super_compare(s_word, t_word):
                self.mark_range(j, j, 'normal')
                self.history_map[i] = j
                self._add_trace(j, i) # v6.0 Secure Trace
                i += 1
                j += 1
                continue
            
            # -------------------------------------------------
            # KROK 2: TOLERANCJA (STOP WORDS)
            # -------------------------------------------------
            if s_word in STOP_WORDS and t_word in STOP_WORDS:
                self.mark_range(j, j, 'normal')
                self.history_map[i] = j
                self._add_trace(j, i) # v6.0 Secure Trace
                i += 1
                j += 1
                continue

            # -------------------------------------------------
            # KROK 3: INSERTION LOOKAHEAD (PATCH v5.9)
            # -------------------------------------------------
            if j + 1 < self.t_len and self.super_compare(s_word, self.trans_tokens[j+1]):
                self.mark_range(j, j, 'bad')
                j += 1
                continue

            # -------------------------------------------------
            # KROK 4: FUZZY LOGIC (TYPO / MERGE / SPLIT)
            # -------------------------------------------------
            match_found = False
            
            # 1:1
            if check_fuzzy_match(s_word, t_word):
                self.mark_range(j, j, 'typo', is_auto=True)
                self.history_map[i] = j
                self._add_trace(j, i) # v6.0 Secure Trace
                i += 1; j += 1
                match_found = True
            # Merge 1:2
            elif j + 1 < self.t_len and check_fuzzy_match(s_word, t_word + self.trans_tokens[j+1]):
                self.mark_range(j, j+1, 'typo', is_auto=True)
                self.history_map[i] = j+1
                self._add_trace(j, i)
                self._add_trace(j+1, i)
                i += 1; j += 2
                match_found = True
            # Split 2:1
            elif i + 1 < self.s_len and check_fuzzy_match(s_word + self.script_tokens[i+1], t_word):
                self.mark_range(j, j, 'typo', is_auto=True)
                self.history_map[i] = j; self.history_map[i+1] = j
                self._add_trace(j, i)
                i += 2; j += 1
                match_found = True
                
            if match_found:
                continue

            # -------------------------------------------------
            # KROK 5: RESYNCHRONIZACJA (DELETION / RETAKE / BAD)
            # -------------------------------------------------

            # Krok 5a: DEEP YELLOW (Deletion Lookahead v6.2/6.3)
            # Sprawdzamy do 4 słów w przód w skrypcie, czy coś pasuje do obecnego transkryptu
            match_offset = -1
            for offset in range(1, 5): # 1 to 4
                if i + offset < self.s_len:
                    s_cand = self.script_tokens[i+offset]
                    # WARUNEK ROZSZERZONY: Exact LUB Fuzzy
                    if self.super_compare(s_cand, t_word) or check_fuzzy_match(s_cand, t_word):
                        match_offset = offset
                        break
            
            if match_offset != -1:
                # Znaleziono zgubę! Słowa od i do i+offset-1 są pominięte w audio (MISSING)
                
                # PATCH v6.3: Rejestracja brakujących indeksów ZANIM przesuniemy 'i'
                for skipped in range(match_offset):
                     self.missing_script_indices.append(i + skipped)

                # Przesuwamy indeks skryptu 'i' do miejsca dopasowania.
                i += match_offset
                continue

            # Krok 5b: Detekcja Retake (Fuzzy Anchor + Lookahead + Distance Penalty v6.5)
            # PATCH v6.5: Zmniejszony limit wsteczny (80) i Distance Penalty
            found_retake = False
            search_limit = max(0, i - 80) # Was 150
            
            for k in range(i - 1, search_limit - 1, -1):
                s_candidate = self.script_tokens[k]
                
                # Weryfikacja kotwicy (Anchor Check)
                is_anchor_candidate = self.super_compare(s_candidate, t_word)
                if not is_anchor_candidate and len(s_candidate) > 3:
                     is_anchor_candidate = check_fuzzy_match(s_candidate, t_word)
                
                if is_anchor_candidate:
                    confirmed = False
                    distance = i - k

                    if distance <= 10:
                        # BLISKO: Logika standardowa (Luźna)
                        # 1. Długie, pewne słowo
                        if len(super_clean(s_candidate)) > 6 and self.super_compare(s_candidate, t_word):
                            confirmed = True
                        # 2. Lookahead (Para słów)
                        elif k + 1 < self.s_len and j + 1 < self.t_len:
                            s_next = self.script_tokens[k+1]
                            lookahead_j = j + 1
                            # Check brief window for next match
                            while lookahead_j < self.t_len and lookahead_j < j + 4:
                                t_next = self.trans_tokens[lookahead_j]
                                if self.super_compare(s_next, t_next) or check_fuzzy_match(s_next, t_next):
                                    confirmed = True
                                    break
                                lookahead_j += 1
                    else:
                        # DALEKO (>10 słów): Logika ścisła (Trigram)
                        # Wymagamy, aby pasowały 3 słowa z rzędu (k, k+1, k+2 -> j, j+1, j+2)
                        # Minimalizuje ryzyko fałszywych dopasowań przy popularnych słowach
                        if k + 2 < self.s_len and j + 2 < self.t_len:
                            s_1 = self.script_tokens[k+1]
                            s_2 = self.script_tokens[k+2]
                            t_1 = self.trans_tokens[j+1]
                            t_2 = self.trans_tokens[j+2]
                            
                            # Używamy super_compare (exact) dla pewności
                            if self.super_compare(s_1, t_1) and self.super_compare(s_2, t_2):
                                confirmed = True

                    if confirmed:
                        j_start = self.history_map.get(k)
                        if j_start is not None and j_start < j:
                            self.mark_range(j_start, j, 'repeat')
                            i = k + 1
                            self.history_map[k] = j 
                            self._add_trace(j, k)
                            j += 1
                            found_retake = True
                            break
            
            if found_retake:
                continue

            # Krok 5c: Błąd (Insertion / Bad) - Fallback
            self.mark_range(j, j, 'bad')
            j += 1
            # i bez zmian
        
        # Cleanup
        if j < self.t_len:
            self.mark_range(j, self.t_len - 1, 'bad')

        # PATCH v6.3: TAIL CATCH
        # Jeśli skończyło się audio, a został skrypt -> Wszystko do końca jest MISSING
        while i < self.s_len:
            self.missing_script_indices.append(i)
            i += 1
            
        print("--- PHASE C FINISHED. STARTING PHASE D: SMART FRAGMENT FILL ---")
        self._phase_d_smart_fragment_fill()
        
        # --- PHASE E: COVERAGE VALIDATION (PATCH v6.7) ---
        # The ultimate filter: if a script index was EVER matched (even as a retake or typo),
        # it is NOT missing. We check history_map which records all successful matches.
        
        real_missing = []
        for s_idx in self.missing_script_indices:
            if s_idx not in self.history_map:
                real_missing.append(s_idx)
        
        self.missing_script_indices = real_missing
        print(f"[Phase E] Coverage Validation complete. Final missing count: {len(self.missing_script_indices)}")

        # PATCH v6.4: ANTI-FREEZE HYBRID RETURN
        # Zamiast krotki, zwracamy listę (AnalysisResult), która ma atrybut .missing_indices.
        result = AnalysisResult(self.words_data)
        result.missing_indices = self.missing_script_indices
        return result

    # ==========================================
    # PHASE D: SMART FRAGMENT FILL (PATCH v5.8)
    # ==========================================
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

        print(f"[Phase D] Analyzing {len(sorted_script_indices)} unique script words...")

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
            local_start = times[0]
            local_end = times[-1]
            
            self.mark_range(local_start, local_end, 'repeat')
            count_retakes += 1

        print(f"--- PHASE D COMPLETED. Processed {count_retakes} genuine retake groups. ---")


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
    
    print("[DEBUG] Applying RGB Pattern to all words...")
    
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

def compare_script_to_transcript(script_text, words_data):
    """
    Wrapper dla silnika v5.0.
    Includes Debug Interceptor for "$ R G B" code.
    """
    
    # --- DEBUG INTERCEPTOR ---
    clean_code = script_text.strip().replace(" ", "").upper()
    if clean_code == "$RGB":
        return apply_debug_rgb_pattern(words_data)
    # -------------------------

    engine = CompareEngineV5(script_text, words_data)
    # PATCH v6.4: ANTI-FREEZE
    # Return single object (AnalysisResult) instead of tuple to keep engine.py happy.
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

def analyze_repeats(words_data, show_inaudible=True):
    """Legacy Standalone Analyzer (Without Script)."""
    # 1. Smart Reset - Wipeout omijający halucynacje, inaudible i ręczne poprawki
    for w in words_data:
        if w.get('_is_hallucination') or w.get('type') in ['silence', 'inaudible'] or w.get('is_inaudible'):
            continue
            
        # Wyczyść tylko to co jest przypisane jako repeat (żeby nie psuć np. bad z engine)
        if w.get('status') == 'repeat':
            w['status'] = w.get('manual_status') # Przywracamy warstwę bazową
            w['selected'] = (w['status'] in ['bad', 'inaudible', 'typo'])
            w['is_auto'] = False

    # 2. Linear Flow
    linear_flow = []
    for idx, w in enumerate(words_data):
        if w.get('type') in ['silence', 'inaudible']: continue
        if w.get('is_inaudible'): continue
        if w.get('_is_hallucination'): continue # SKIPPING HALLUCINATIONS
        
        txt = re.sub(r'[^\w]', '', w['text']).lower()
        if not txt or txt in STOP_WORDS: continue
        linear_flow.append({'text': txt, 'real_idx': idx})

    n_flow = len(linear_flow)
    marked_indices = set()
    
    # 3. N-gram
    i = 0
    LOOKAHEAD = 30
    MIN_LEN = 2
    
    while i < n_flow:
        curr = linear_flow[i]
        limit = min(n_flow, i + LOOKAHEAD)
        best_len = 0
        best_target = -1
        
        for j in range(i + 1, limit):
            target = linear_flow[j]
            if curr['text'] == target['text']:
                k = 1
                while (i + k < n_flow) and (j + k < n_flow):
                    if linear_flow[i+k]['text'] == linear_flow[j+k]['text']: k += 1
                    else: break
                
                if k >= MIN_LEN and k > best_len:
                    best_len = k
                    best_target = j
        
        if best_len >= MIN_LEN:
            for m in range(best_len):
                marked_indices.add(linear_flow[i+m]['real_idx'])
                marked_indices.add(linear_flow[best_target+m]['real_idx'])
        i += 1

    count = 0
    for idx in marked_indices:
        words_data[idx]['status'] = 'repeat'
        words_data[idx]['selected'] = False
        count += 1
        
    return words_data, count

# ==========================================
# 6. GUI LOGIC HELPERS (Decoupled Logic)
# ==========================================

def apply_auto_filler_logic(words_data, filler_words, enabled):
    """
    Applies logic for auto-marking filler words.
    Extracted from GUI to keep presentation layer clean.
    """
    # Use a set for faster O(1) lookups instead of list O(n)
    dynamic_bad = {w.lower().strip() for w in filler_words}
    
    for w in words_data:
        if w.get('is_inaudible') or w.get('type') == 'silence' or w.get('_is_hallucination'):
            continue
        
        txt_clean = re.sub(r'[^\w\s\'-]', '', w['text']).strip()
        if txt_clean.lower() in dynamic_bad:
            if enabled:
                # Mark as bad if currently neutral or already bad
                if w.get('status') is None or w.get('status') == 'bad':
                    w['status'] = 'bad'
                    w['selected'] = True
            else:
                # Unmark if disabled, but only if it was marked as bad
                if w.get('status') == 'bad':
                    w['status'] = None
                    w['selected'] = False
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