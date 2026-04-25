#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: algorythms.py
ROLE: Tool Layer
DESCRIPTION:
CORE LOGIC v6.4 (STABLE) - Script vs Transcript Alignment.
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
- Handling of Deletions and Insertions
- Document readers (PDF/DOCX)
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
        return "\n".join(text_parts)
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
                text += extracted + "\n"
        return text
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
        
        # Filtrowanie transkryptu
        self.trans_tokens = []
        self.trans_indices = [] 
        
        for idx, w in enumerate(words_data):
            if w.get('type') == 'silence' or w.get('is_inaudible'):
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

    def mark_range(self, t_start_idx, t_end_idx, status):
        """Oznacza zakres w words_data (indeksy wirtualne -> rzeczywiste)."""
        for k in range(t_start_idx, t_end_idx + 1):
            if k >= self.t_len: break
            real_idx = self.trans_indices[k]
            w = self.words_data[real_idx]
            
            # Reset
            w['status'] = None
            w['selected'] = False
            
            if status != 'normal':
                w['status'] = status
                w['selected'] = True

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
        
        print(f"--- STARTING COMPARE v6.4 (Script: {self.s_len}, Trans: {self.t_len}) ---")

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
                self.mark_range(j, j, 'typo')
                self.history_map[i] = j
                self._add_trace(j, i) # v6.0 Secure Trace
                i += 1; j += 1
                match_found = True
            # Merge 1:2
            elif j + 1 < self.t_len and check_fuzzy_match(s_word, t_word + self.trans_tokens[j+1]):
                self.mark_range(j, j+1, 'typo')
                self.history_map[i] = j+1
                self._add_trace(j, i)
                self._add_trace(j+1, i)
                i += 1; j += 2
                match_found = True
            # Split 2:1
            elif i + 1 < self.s_len and check_fuzzy_match(s_word + self.script_tokens[i+1], t_word):
                self.mark_range(j, j, 'typo')
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
                # (Lookahead loop per instruction)
                for skipped in range(match_offset):
                     self.missing_script_indices.append(i + skipped)

                # Przesuwamy indeks skryptu 'i' do miejsca dopasowania.
                i += match_offset
                continue

            # Krok 5b: Detekcja Retake (Fuzzy Anchor + Lookahead)
            found_retake = False
            search_limit = max(0, i - 150)
            
            for k in range(i - 1, search_limit - 1, -1):
                s_candidate = self.script_tokens[k]
                is_anchor_candidate = self.super_compare(s_candidate, t_word)
                if not is_anchor_candidate and len(s_candidate) > 3:
                     is_anchor_candidate = check_fuzzy_match(s_candidate, t_word)
                
                if is_anchor_candidate:
                    confirmed = False
                    if len(super_clean(s_candidate)) > 6 and self.super_compare(s_candidate, t_word):
                        confirmed = True
                    elif k + 1 < self.s_len and j + 1 < self.t_len:
                        s_next = self.script_tokens[k+1]
                        lookahead_j = j + 1
                        while lookahead_j < self.t_len and lookahead_j < j + 4:
                            t_next = self.trans_tokens[lookahead_j]
                            if self.super_compare(s_next, t_next) or check_fuzzy_match(s_next, t_next):
                                confirmed = True
                                break
                            lookahead_j += 1
                    
                    if confirmed:
                        j_start = self.history_map.get(k)
                        if j_start is not None and j_start < j:
                            self.mark_range(j_start, j, 'repeat')
                            i = k + 1
                            self.history_map[k] = j 
                            self._add_trace(j, k) # v6.0 Secure Trace
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
        
        # PATCH v6.4: ANTI-FREEZE HYBRID RETURN
        # Zamiast krotki, zwracamy listę (AnalysisResult), która ma atrybut .missing_indices.
        # To naprawia błąd w engine.py, który oczekuje iterowalnej listy słów.
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

def compare_script_to_transcript(script_text, words_data):
    """
    Wrapper dla silnika v5.0.
    """
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
    # 1. Reset
    for w in words_data:
        if w.get('status') == 'repeat':
            w['status'] = None
            w['selected'] = False

    # 2. Linear Flow
    linear_flow = []
    for idx, w in enumerate(words_data):
        if w.get('type') in ['silence', 'inaudible']: continue
        if w.get('is_inaudible'): continue
        
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