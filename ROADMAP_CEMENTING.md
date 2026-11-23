# Plan uporządkowania i zacementowania BadWords (`ROADMAP_CEMENTING.md`)

> **Cel dokumentu:** Uporządkowanie, dopracowanie i zabezpieczenie **obecnie istniejących** funkcji BadWords tak, aby działały niezawodnie na Windowsie, Linuksie i macOS oraz nie psuły się przy kolejnych zmianach.
>
> **Jak z tego korzystać:** Wybierasz jeden otwarty punkt (`[ ]`) na jedną sesję, kopiujesz gotowy **Prompt do wklejenia** do nowej rozmowy z AI i idziesz zrobić herbatę.
> - Agent najpierw **tylko analizuje** obszar (z uwzględnieniem **aktualnej dokumentacji DaVinci Resolve 21.1+ i ograniczeń wersji Free**) i przedstawia raport oparty na **konkretnych, życiowych przypadkach od strony użytkownika** (bez suchych haseł i żargonu) wraz z pytaniami decyzyjnymi.
> - Dopiero po Twoich odpowiedziach wdraża zmiany, **testuje mechanizmy na żywo** (nie tylko na makietach), sprawdza automatycznie wszystko, co dotyczy Windowsa 11 lub czystego Linuksa w lokalnych wirtualkach (`badwords-win11`, `badwords-linux-kde`), przygotowuje **krótką instrukcję krok po kroku po polsku** dla testów ręcznych/wizualnych lub z programem zewnętrznym, robi i ogląda **zrzuty ekranu** zmian widocznych dla użytkownika, wpisuje pełną dokumentację do `docs/CEMENTED.md`, aktualizuje `docs/DEV_STATE.md`, dopisuje krótkie hasło w `.agents/rules/architecture.md` (Sekcja 3) **oraz odhacza zakończony punkt tutaj (`[x]` + `✅ ZAKOŃCZONO`)**.
> - Gdy podczas rozmowy wskażesz jakąś uwagę albo brakujący krok, agent automatycznie zapisuje tę lekcję w `.agents/rules/lessons_and_standards.md`, abyś w kolejnych sesjach nie musiał prosić o to samo.

---

## Postęp prac (Checklista punktów 1-22)

> *Poniższa lista pozwala od razu sprawdzić, co zostało już w pełni zamknięte i zabezpieczone, a co czeka na swoją sesję.*

- [x] **Punkt 1** - Start aplikacji, dobór środowiska Pythona i „samoleczenie” przy uruchomieniu *(✅ ZAKOŃCZONO 2026-11-23 → `docs/CEMENTED.md` Sekcja 6)*
- [x] **Punkt 2** - Rozdzielenie trybu roboczego (DEV) od wersji dla użytkownika oraz porządek w plikach danych *(✅ ZAKOŃCZONO 2026-11-23 → `docs/CEMENTED.md` Sekcja 8)*
- [ ] **Punkt 3** - Okno bez ramki, własny pasek tytułu, tryb „Zawsze na wierzchu” i płynność animacji między systemami
- [ ] **Punkt 4** - Spójność języków, brak emoji i tekstów na sztywno, wygląd paska postępu i skalowanie interfejsu
- [ ] **Punkt 5** - Wyciąganie dźwięku z wideo/osi, normalizacja głośności i wstępne wykrywanie ciszy
- [ ] **Punkt 6** - Wykrywanie karty graficznej (NVIDIA / Apple Silicon / procesor) i bezpieczny powrót na procesor
- [ ] **Punkt 7** - Pobieranie modeli AI, uruchamianie transkrypcji i strumieniowanie słów na żywo
- [ ] **Punkt 8** - Wykrywanie powtórek, słów-wypełniaczy, fragmentów niezrozumiałych i ochrona ręcznych oznaczeń
- [ ] **Punkt 9** - Wczytywanie scenariuszy (DOCX/PDF/TXT), porównanie ze scenariuszem i widok obok siebie (Side-by-Side)
- [ ] **Punkt 10A** - Odchudzenie głównego okna (cz. 1): statystyki cięć, legenda kolorów, podgląd przekreśleń i eksport tekstu
- [ ] **Punkt 10B** - Odchudzenie głównego okna (cz. 2): paski boczne, skróty klawiszowe, obsługa zdarzeń i przyciski markerów
- [ ] **Punkt 10C** - Odchudzenie głównego okna (cz. 3): zadania w tle, sprawdzanie aktualizacji, komunikaty statusu i zamykanie
- [ ] **Punkt 11** - Ekran powitalny: przełączanie źródła, kolejka plików lokalnych, wybór ścieżek i Szybka Cisza
- [ ] **Punkt 12A** - Płótno transkrypcji: zaznaczanie ramką i tekstem, malowanie, przekreślenia, wyszukiwarka i Cofnij/Ponów
- [ ] **Punkt 12B** - Wydajność edycji i przeliczania cięć na wielogodzinnych nagraniach (zgłoszenie GitHub `#20`)
- [ ] **Punkt 13** - Dolny odtwarzacz audio/wideo, omijanie cięć w czasie rzeczywistym i regulacja głośności
- [ ] **Punkt 14** - Wykres fali dźwiękowej, podgląd wideo 360p (proxy) oraz suwaki ciszy na żywo
- [ ] **Punkt 15** - Okno Ustawień i biblioteka własnych kontrolek interfejsu
- [ ] **Punkt 16** - Łączność z DaVinci Resolve, mostek dla darmowej wersji 21.1+ i praca całkowicie bez Resolve
- [ ] **Punkt 17** - Dokładność klatkowa i montaż osi czasu w DaVinci Resolve (XML vs natywny DRT)
- [ ] **Punkt 18** - Eksport dla innych programów montażowych w trybie niezależnym (XML, FCPXML, OTIO, EDL i cięcie pliku)
- [ ] **Punkt 19** - Zapis projektu (`.bws`), autozapis, odzyskiwanie po awarii i okno niezapisanych zmian
- [ ] **Punkt 20** - Nowoczesny instalator, uruchamiacze (launchery) i porządek ze starym instalatorem
- [ ] **Punkt 21** - Jedna, spójna ścieżka aktualizacji aplikacji i usunięcie powielonych skryptów
- [ ] **Punkt 22** - Telemetria, zgłaszanie błędów z logami oraz automatyczne testy i kontrola wydań

---

## Przegląd etapów

1. **Etap 1 (v4.1): Fundamenty, start aplikacji i spójność systemowa** - punkty 1-4 *(ukończono: 2/4)*
2. **Etap 2 (v4.2): Dźwięk, transkrypcja AI i analiza tekstu** - punkty 5-9 *(ukończono: 0/5)*
3. **Etap 3 (v4.3): Ekran powitalny, edytor, podgląd audio/wideo i okna ustawień** - punkty 10A-10C, 11, 12A-12B, 13-15 *(ukończono: 0/9)*
4. **Etap 4 (v4.4): DaVinci Resolve, montaż osi czasu, eksport i zapis projektów** - punkty 16-19 *(ukończono: 0/4)*
5. **Etap 5 (v4.5): Instalator, aktualizacje, zgłaszanie błędów i sprzątanie** - punkty 20-22 *(ukończono: 0/3)*

---

## Powiązane zgłoszenia z GitHuba (stan bieżący)

- **Otwarte zgłoszenie `#20`** (*lagowanie aplikacji przy filmach trwających ponad 3-5 godzin za każdym razem, gdy słowo jest zaznaczane na czerwono*) → wpięte bezpośrednio do **Punktu 12B** (oraz powiązane z **Punktem 10A** i **14**).
- **Otwarte zgłoszenie `#8`** (*propozycja nowej dużej funkcji: nieliniowe dopasowanie scenariusza i obsługa pracy z AI przy wywiadach*) → uwzględnione jako kontekst przyszłego rozwoju przy porządkowaniu „pod spodem” w **Punkcie 9** (nie wdrażamy tej nowej funkcji podczas cementowania i nie zamykamy zgłoszenia `#8`).
- **Zamknięte zgłoszenia do weryfikacji, czy nic nie wróciło (`#19`, `#18`, `#7`, `#5`, `#3`)** → wplecione w odpowiednie punkty (`1` [zweryfikowano i zamknięto w Punkcie 1], `6`, `7`, `16`, `20`), aby upewnić się, że dawne poprawki są kompletne i zabezpieczone testami.

---

## Etap 1 (v4.1): Fundamenty, start aplikacji i spójność systemowa

> Najbardziej kruche elementy, od których zależy to, czy aplikacja w ogóle się uruchomi, nie pomiesza danych roboczych z plikami programu i będzie wyglądać oraz zachowywać się poprawnie na każdym systemie.

---

### 1. ✅ [ZAKOŃCZONO 2026-11-23] Start aplikacji, dobór środowiska Pythona i „samoleczenie” przy uruchomieniu

> **Status:** ✅ **ZAKOŃCZONO I ZACEMENTOWANO (2026-11-23)**
> **Co zostało naprawione dla użytkownika:**
> - Ekran powitalny pojawia się natychmiast po kliknięciu ikony (bez czekania na ciężkie ładowanie reszty aplikacji i skanowanie karty graficznej na starcie).
> - Program twardo odcina się od obcych instalacji Pythona / Conda na komputerze, a w razie brakujących składników najpierw pyta użytkownika o zgodę w stylizowanym ciemnym oknie w jego języku.
> - W razie krytycznego błędu startu pokazuje czytelne okno z powodem, ścieżką do logu i opcjonalnym wysyłaniem raportu za zgodą (spójnym z zakładką Kontakt).
> - Ujednolicono uruchamianie z DaVinci Resolve (z zachowaniem zgodności z Resolve Free 21.1+, gdzie skrypt Pythona nie uruchamia się ze środka Resolve, ale nie jest też kasowany) oraz zabezpieczono natywne uruchamiacze na Windowsie, Linuksie i macOS.
> **Gdzie opisano szczegóły i testy:** `docs/CEMENTED.md` (Sekcja 6), `docs/DEV_STATE.md` (Sekcja 4, pkt 8), testy w `tests/test_startup_guard.py`.

<details>
<summary>Archiwalny prompt zrealizowanego punktu 1 (punkt zamknięty - nie uruchamiaj ponownie)</summary>

```text
Przeanalizuj punkt 1 planu cementowania: Start aplikacji, środowisko uruchomieniowe i mechanizm samoleczenia przy starcie.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie dogłębną analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i powiązane z nimi elementy:
   - src/main.py
   - raport/message.txt (znany przypadek błędu zgodności wersji Pythona przy starcie z Resolve)
   - sekcja startu i wykrywania środowiska w src/osdoc.py
   - wywołania uruchamiania z zewnętrznych skryptów w setupfiles/windows/, setupfiles/linux/, setupfiles/macos/
   - zgłoszenie GitHub #18 (sprawdź przez `gh issue view 18`, czy problem błędu uruchamiania ze ścieżkami jest w pełni rozwiązany zarówno przy starcie z pulpitu, jak i z Resolve) oraz otwarte zgłoszenia przez `gh issue list --state open`, czy pojawiło się coś nowego w tym obszarze.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź, czy obecne rozwiązanie jest optymalne i spójne między systemami Windows, Linux i macOS (szczególnie uruchamianie jako samodzielna aplikacja vs uruchamianie ze środka DaVinci Resolve oraz ochrona przed cudzym środowiskiem Pythona / Conda).
4. Przygotuj dla mnie po polsku, całkowicie prostym, nietechnicznym językiem (bez nazw funkcji, klas i bez wklejania kodu), zwięzły raport z dokładnie 3 sekcjami:
   (A) Co w tym miejscu wygląda dziwnie lub podejrzanie (jakie są wbudowane obejścia i „łaty” - czy powinny zostać, czy można je bezpiecznie uprościć)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. długie uruchamianie, ciche błędy, konflikty między systemowym Pythonem a wbudowanym środowiskiem, niepotrzebne próby naprawy z internetu)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak dokładnie ma się zachowywać start i awaryjne komunikaty / czego program ma NIE robić bez mojej zgody), żebym mógł krótko odpowiedzieć punkt po punkcie.

Po mojej akceptacji i wdrożeniu zmian pamiętaj o:
- napisaniu testów blokujących regresję (w tests/ i uruchomieniu run_tests.py),
- ewentualnym zamknięciu rozwiązanych powiązanych zgłoszeń na GitHubie przez `gh` (jeśli jakieś otwarte dotyczyły tego punktu),
- wpisaniu pełnej dokumentacji technicznej (działanie, niezmienniki, testy) do docs/CEMENTED.md oraz dopisaniu wyłącznie krótkiego, 3-4 wyrazowego hasła z odesłaniem do docs/CEMENTED.md w .agents/rules/architecture.md (Sekcja 3, z zachowaniem limitu poniżej 4 000 znaków).
```

</details>

---

### 2. ✅ [ZAKOŃCZONO 2026-11-23] Rozdzielenie trybu roboczego (DEV) od wersji dla użytkownika oraz porządek w plikach danych

> **Status:** ✅ **ZAKOŃCZONO I ZACEMENTOWANO (2026-11-23)**
> **Co zostało naprawione dla użytkownika:**
> - Wydzielono czysty moduł zarządzania danymi, ścieżkami, atomowym zapisem ustawień, logowaniem i plikami tymczasowymi (`src/config/runtime_data.py`), odciążając `src/osdoc.py`.
> - Wprowadzono atomowy zapis `settings.json` i `user.json` z automatyczną kopią `.bak` i odzyskiwaniem kluczy w razie uszkodzenia pliku (np. po nagłym wyłączeniu prądu) oraz bezpieczny folder zapasowy w stałym profilu użytkownika (`AppData\Local\BadWords`, `~/Library/Application Support/BadWords`, `~/.local/share/BadWords`) zamiast ulotnego katalogu `Temp` przy braku praw zapisu w folderze instalacji.
> - Wyeliminowano podwójne zapisywanie tych samych linijek i błędów w `badwords_debug.log` po uruchomieniu przez natywny uruchamiacz oraz dodano przycinanie pliku logu powyżej 5 MB na starcie (z zachowaniem najnowszych 2,5 MB historii).
> - Zabezpieczono pliki tymczasowe aktywnie otwartego projektu przed skasowaniem podczas wielogodzinnych sesji montażowych (domyślny próg sprzątania starych, nieużywanych plików to 24 godziny, a jednorazowe skrypty pomocnicze znikają od razu po zamknięciu).
> - Dodano automatyczną obsługę kontenerów DaVinci Resolve z Mac App Store (`~/Library/Containers/...`), krótkie ścieżki Windows 8.3 w `BadWords Bridge.lua` dla kont z polskimi znakami, usunięto sztywne ścieżki `/mnt/dump/...` oraz naprawiono odwołania `log_warning` i `osdoc.load_preferences()`.
> **Gdzie opisano szczegóły i testy:** `docs/CEMENTED.md` (Sekcja 2 i Sekcja 8), `docs/DEV_STATE.md` (Sekcja 4, pkt 11), testy w `tests/test_runtime_data_and_isolation.py`.

<details>
<summary>Archiwalny prompt zrealizowanego punktu 2 (punkt zamknięty - nie uruchamiaj ponownie)</summary>

```text
Przeanalizuj punkt 2 planu cementowania: Rozdzielenie trybu deweloperskiego od wersji zainstalowanej oraz zarządzanie plikami danych, zapisami i logami.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i foldery:
   - src/osdoc.py (wykrywanie trybu roboczego, foldery ustawień, zapisów, plików tymczasowych, logowanie, migracja starych ustawień, sprzątanie starych plików)
   - src/config/settings_defaults.py
   - src/engine/preferences.py (w części dotyczącej odczytu i zapisu preferencji)
   - raport/logi_macOS_prawdopodobnie_blad_pobierania_ffmpega.log (zwróć uwagę na powielone wpisy w logach)
   - sprawdź przez `gh issue list --state open`, czy któreś otwarte zgłoszenie dotyczy ścieżek danych lub logów.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność zachowania na Windowsie, Linuksie i macOS (uprawnienia do folderów, długie ścieżki i polskie znaki np. w nazwie użytkownika Windowsa, podwójne zapisywanie wpisów w logu, bezpieczne czyszczenie folderu tymczasowego przy otwartych kilku projektach lub długich sesjach oraz ścieżki wymiany dla aktualnego DaVinci Resolve 21.1+ i wersji z Mac App Store).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA (zamiast suchych haseł opisz krok po kroku, co użytkownik robi, co dokładnie widzi na ekranie i co mu przestaje działać):
   (A) Co w tym miejscu wygląda dziwnie lub podejrzanie (dla każdego obejścia i starej migracji opisz realny przypadek: jaka katastrofa lub strata danych wydarzyłaby się u użytkownika, gdybyśmy to wyłączyli, i czy da się to bezpiecznie uprościć)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie w oczach użytkownika (konkretne scenariusze krok po kroku: np. użytkownik na Windowsie z polskim nazwiskiem w ścieżce traci ustawienia po aktualizacji, na macOS po błędzie FFmpeg dostaje zdublowane logi nieczytelne dla wsparcia, albo po kilku długich filmach kończy mu się miejsce na dysku bo czyszczenie pomija albo kasuje aktywny projekt)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz wprost, jak dokładnie zmieni się zachowanie widziane przez użytkownika (jak długo trzymamy pliki tymczasowe, czego migracja ma NIE dotykać).

Po mojej akceptacji i wdrożeniu: napisz testy ochronne (w tests/ i uruchom run_tests.py), przetestuj na żywo realny zapis/migrację/czyszczenie w bezpiecznym folderze testowym (nie tylko na makietach), wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 2 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

</details>

---

### 3. Okno bez ramki, własny pasek tytułu, tryb „Zawsze na wierzchu” i płynność animacji między systemami

- **Co obejmuje:** Wygląd i zachowanie głównego okna oraz wyskakujących okienek: przeciąganie za górny pasek, powiększanie na pełny ekran na wybranym monitorze, chowanie białych mignięć przy otwieraniu okien, **wyeliminowanie ~3 mignięć mikro-okienek na Windows 11 podczas startu aplikacji (powiązanych z inicjalizacją okna ustawień - zanotowane z testów VM 2026-11-23)**, znikająca ikona aplikacji, przycisk „Zawsze na wierzchu” oraz dopasowanie płynności animacji do odświeżania monitora (60 Hz / 120 Hz / 144 Hz+).
- **Dlaczego to ważne:** Każdy z trzech systemów (Windows 11, macOS, Linux z X11 lub Waylandem) traktuje okna bez systemowej ramki zupełnie inaczej. To jedno z najczęstszych źródeł wizualnych usterek, zacinania przeciągania okna lub błędów przy zmianie monitora.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Część sztuczek do okien i ikon siedzi w głównym oknie i w oknie ustawień zamiast w jednym wspólnym miejscu. Uporządkowanie ich w jednym wspólnym mechanizmie okien sprawi, że każde nowe okienko dodane w przyszłości od razu dostanie dobry wygląd i zachowanie na wszystkich trzech systemach.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 3 planu cementowania: Zachowanie okien bez ramki, paska tytułu, ikony aplikacji, trybu „Zawsze na wierzchu” oraz synchronizacji odświeżania ekranu.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/components/mixins.py
   - src/gui/components/titlebar.py
   - src/gui/utils.py
   - src/gui/vsync.py
   - metody okna i odświeżania w src/osdoc.py (wymuszanie ciemnego paska, zawsze na wierzchu)
   - fragmenty dotyczące odświeżania ikony, pełnego ekranu i „Zawsze na wierzchu” w src/gui/main_window.py oraz src/gui/dialogs/settings_dialog.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux (X11 i Wayland, KDE/GNOME) oraz macOS (ikona w Docku, skróty okna, brak białego błysku przy otwieraniu, zachowanie na wielu monitorach o różnym skalowaniu i odświeżaniu).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA (krok po kroku, co widzi i klika człowiek przed ekranem):
   (A) Co wygląda dziwnie lub podejrzanie (dla każdej systemowej sztuczki opisz, jaki konkretny brzydki błąd ekranu pojawiłby się u użytkownika bez niej - np. białe mignięcie, brak przyciągania do krawędzi, brak paska na ekranie)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie w oczach użytkownika (konkretne scenariusze: np. użytkownik przeciąga okno z ekranu laptopa 150% na monitor 100% i okno ucina przyciski, na Linuksie Wayland klika maksymalizację i okno przykrywa pasek zadań, albo włącza „Zawsze na wierzchu” nad DaVinci Resolve i okno i tak chowa się pod spód)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji wyjaśnij dokładnie, jak okno ma się zachować przed oczami użytkownika (na drugim monitorze, po maksymalizacji, na macOS i Linuksie).

Po mojej akceptacji i wdrożeniu: napisz testy i zweryfikuj na żywo działanie prawdziwego okna (rozmiary, kliknięcia, płynność), wygeneruj zrzuty ekranu (PNG) zmienionych okien i sam je obejrzyj przed odpowiedzią, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 3 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 4. Spójność języków, brak emoji i tekstów na sztywno, wygląd paska postępu i skalowanie interfejsu

- **Co obejmuje:** Zgodność wszystkich 11 wersji językowych, usuwanie tekstów wpisanych „na sztywno” (np. po polsku mimo wybranego angielskiego), całkowite wyeliminowanie systemowych emotek z interfejsu na rzecz czystych ikon wektorowych, ochronę przed narzucaniem systemowych kolorów (np. czarny tekst na czarnym tle) oraz poprawne skalowanie (75%-150%) i zaokrąglenia pasków postępu.
- **Dlaczego to ważne:** Testerzy zgłaszali dokładnie te problemy w raportach: polskie dymki podpowiedzi przy włączonym angielskim języku, czarny tekst na ciemnym tle, kwadratowo przycięte rogi paska postępu oraz ostrzeżenia o nieobsługiwanym stylu czcionki w dolnym odtwarzaczu.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Pomocniczy przycisk informacji „(i)” oraz rysowanie ikon wektorowych są powielone w kilku plikach zamiast być w jednym miejscu, a część okienek ma własne słowniczki zamiast korzystać z centralnych tłumaczeń. Scalenie tego bardzo ułatwi dodawanie kolejnych ekranów i języków.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 4 planu cementowania: Spójność tłumaczeń, usunięcie tekstów i emoji wpisanych na sztywno, odporność kolorów motywu na systemowe style, paski postępu oraz skalowanie ekranu.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te obszary:
   - src/i18n/ (mechanizm ładowania i wszystkie pliki językowe)
   - src/config/app_constants.py, src/config/palette.py, src/config/languages.py
   - src/gui/widgets/progress_bar.py i użycie pasków postępu w src/gui/views/processing_view.py oraz src/gui/dialogs/splash_screen.py
   - miejsca z potencjalnym tekstem lub emoji na sztywno w src/gui/dialogs/ (m.in. export_dialog.py, v4_migration_dialog.py, settings_dialog.py), src/gui/main_window.py, src/gui/components/audio_preview.py, src/gui/components/video_preview.py
   - raport/raport.md (zgłoszenia testerów o czarnym tekście na czarnym tle, języku podpowiedzi i przyciętych rogach paska postępu)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux (zwłaszcza KDE/GTK narzucające własną paletę) i macOS przy różnych poziomach powiększenia interfejsu (75%-150%).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA (wskaż konkretne miejsca na ekranach, które widzi użytkownik):
   (A) Co wygląda dziwnie lub podejrzanie (gdzie ominięto system tłumaczeń albo powielono rysowanie ikon i dlaczego ktoś to tak zostawił)?
   (B) Co obecnie psuje doświadczenie użytkownika (konkretne sytuacje z życia i raportów testerów: np. użytkownik wybiera język angielski, najeżdża na ikonkę usuwania pliku lub podpowiedź i nadal czyta tekst po polsku; ma jasny motyw systemu i widzi czarny napis na czarnym przycisku; przy 125%-150% powiększenia ucina mu rogi paska lub widzi systemową emotkę zamiast ikony aplikacji)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz, co dokładnie zobaczy użytkownik (np. jak wygląda ikona zamiast emotki, jak zachowuje się aplikacja przy brakującym tłumaczeniu lub nietypowym skalowaniu).

Po mojej akceptacji i wdrożeniu: uruchom testy regresyjne i wizualne (tests/ + run_tests.py), sprawdź na żywo przełączanie języków i skali (75%-150%) w uruchomionym oknie, wygeneruj zrzuty ekranu wszystkich zmienionych ekranów/pasków i sam je obejrzyj przed odpowiedzią, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 4 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

## Etap 2 (v4.2): Dźwięk, transkrypcja AI i analiza tekstu

> Serce sztucznej inteligencji i obliczeń w BadWords: przygotowanie dźwięku, bezpieczne wykorzystanie karty graficznej lub procesora, rozpoznawanie mowy oraz porównywanie ze scenariuszem i wykrywanie powtórek.

---

### 5. Wyciąganie dźwięku z wideo/osi, normalizacja głośności i wstępne wykrywanie ciszy

- **Co obejmuje:** Wyszukiwanie narzędzia FFmpeg na komputerze użytkownika, wyciąganie ścieżki dźwiękowej z plików wideo lub audio, wyrównywanie głośności przed analizą, wykrywanie fragmentów ciszy oraz łączenie krótkich wypowiedzi w dłuższe paczki („wyspy dźwięku”) dla AI.
- **Dlaczego to ważne:** Z logów wynikał problem z brakiem wykrywania FFmpeg na macOS. Dodatkowo od jakości wyciągniętego dźwięku i łączenia pauz zależy dokładność zarówno cięcia ciszy, jak i całej transkrypcji - przy długich lub wielokanałowych plikach drobny błąd powoduje przesunięcia w czasie lub brak dźwięku.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Logika wyciągania dźwięku jest podzielona między dwa pliki silnika (jeden robi podstawową obróbkę i normalizację, drugi składa wiele plików i bada ich parametry). Zebranie reguł pracy z mediami i FFmpeg w jedno czytelne miejsce ułatwi w przyszłości obsługę np. wielu ścieżek lektorów naraz.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 5 planu cementowania: Wyszukiwanie FFmpeg, wyciąganie dźwięku z klipów, normalizacja głośności, wykrywanie ciszy i grupowanie fragmentów mowy.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i powiązania:
   - src/engine/audio_extraction.py
   - część przygotowania mediów i łączenia dźwięku w src/engine/audio_engine.py
   - wyszukiwanie narzędzia FFmpeg w src/osdoc.py
   - raport/logi_macOS_prawdopodobnie_blad_pobierania_ffmpega.log
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź, czy rozwiązanie jest optymalne i spójne między Windows, Linux i macOS (różne formaty wideo/audio, ścieżki ze spacjami lub polskimi znakami, bardzo długie nagrania, pliki bez dźwięku albo z kilkoma ścieżkami audio, oraz ścieżki klipów przekazywane z DaVinci Resolve w tym przez mostek Lua w wersji Free 21.1+).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia siedzą przy szukaniu FFmpeg, normalizacji i łączeniu „wysp mowy” - co realnie zepsułoby się w nagraniu użytkownika, gdybyśmy je wyjęli)?
   (B) Co obecnie może się psuć w oczach użytkownika (konkretne przypadki: np. użytkownik na macOS wrzuca film i po kliknięciu Analizuj widzi błąd FFmpeg mimo że program go pobierał; wrzuca nagranie ekranu bez ścieżki audio albo grę z 2 ścieżkami audio i transkrypcja analizuje pustkę lub grę zamiast mikrofonu; przy 3-godzinnym pliku czeka bardzo długo bez informacji o etapie)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz jasno, co zobaczy użytkownik i co dostanie na ekranie (komunikat przy braku dźwięku, wybór ścieżki, brak FFmpeg).

Po mojej akceptacji i wdrożeniu: napisz testy blokujące regresję (tests/ + run_tests.py) oraz przetestuj na żywo prawdziwy przebieg FFmpeg na próbce audio/wideo (nie tylko testy na makietach), wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 5 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 6. Wykrywanie karty graficznej (NVIDIA / Apple Silicon / procesor) i bezpieczny powrót na procesor

- **Co obejmuje:** Automatyczne sprawdzanie przed startem transkrypcji, czy komputer ma sprawną kartę graficzną NVIDIA (z wymaganą wersją sterowników i bibliotekami na dysku), czy działa na procesorze Apple Silicon (M1-M5), czy powinien spokojnie przełączyć się na zwykły procesor - bez nagłego zamykania programu.
- **Dlaczego to ważne:** Na słabszych lub szkolnych komputerach, przy niekompletnych sterownikach NVIDIA albo braku części bibliotek graficznych (jak w zgłoszeniu GitHub `#19`), silnik AI potrafił nagle wybuchnąć podczas uruchamiania. Choć wprowadzono już poprawki awaryjne, ten obszar wymaga pełnego sprawdzenia na wszystkich trzech systemach.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Część wykrywania sprzętu leży w module systemowym, a druga w module transkrypcji, przy czym test karty uruchamiany jest przez sklejany dynamicznie tekst skryptu. Uporządkowanie wykrywania sprzętu w jednym miejscu bez sklejanych skryptów bardzo ułatwi dodanie w przyszłości nowych akceleratorów.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 6 planu cementowania: Wykrywanie i weryfikacja sprzętu dla AI (NVIDIA, Apple Silicon, CPU) oraz bezpieczne przełączanie awaryjne na procesor.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te obszary:
   - sprawdzanie karty graficznej, sterowników, bibliotek i doboru wątków procesora w src/osdoc.py
   - sprawdzanie sprawności karty, wybór trybu obliczeń i obsługę Apple Silicon w src/engine/transcription.py
   - testy w tests/test_host_env_fixes.py (żeby zrozumieć, co już jest zabezpieczone)
   - zamknięte zgłoszenie GitHub #19 (`gh issue view 19`) i sprawdź otwarte zgłoszenia (`gh issue list --state open`), czy coś nowego dotyczy CUDA/GPU.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność i bezpieczeństwo na Windowsie, Linuksie i macOS (tryb Auto, ręcznie wymuszone GPU bez karty lub ze starym sterownikiem, komputer z małą ilością pamięci RAM, różnice między Intel Mac a Apple Silicon).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (które obecne zabezpieczenia sterowników i bibliotek chronią użytkownika przed nagłym zamknięciem całego programu przy starcie AI - opisz konkretny przypadek np. szkolnego komputera, gdzie to ratuje pracę)?
   (B) Co obecnie może się psuć w oczach użytkownika (konkretne scenariusze: np. użytkownik ze słabszą kartą albo starszym sterownikiem klika Analizuj, program długo sprawdza sprzęt lub w ogóle znika bez wyjaśnienia; albo w ustawieniach ręcznie wymusił GPU na komputerze bez karty i zamiast czytelnej podpowiedzi dostaje tajemniczy błąd)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji wyjaśnij, co zobaczy użytkownik (np. dyskretne powiadomienie vs ciche przełączenie na procesor, co zrobić gdy ręcznie wybrał GPU a karta nie działa).

Po mojej akceptacji i wdrożeniu: rozbuduj testy w tests/ (uruchom run_tests.py), przetestuj na żywo prawdziwe sondowanie sprzętu i bezpieczny powrót awaryjny na procesor, a jeśli zmienisz okienka/komunikaty ostrzeżeń - wygeneruj i obejrzyj zrzuty ekranu, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 6 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 7. Pobieranie modeli AI, uruchamianie transkrypcji i strumieniowanie słów na żywo

- **Co obejmuje:** Pobieranie wybranych modeli Whisper (oraz wersji dla Apple Silicon) z pokazywaniem postępu, obsługę błędów przy braku sieci lub zablokowaniu zapory (jak opisywano w zgłoszeniach `#3` i `#7`), zgodność z nowszą biblioteką dekodującą audio/wideo, uruchamianie transkrypcji w kawałkach lub w całości oraz pokazywanie słów na żywo w edytorze w trakcie pracy AI.
- **Dlaczego to ważne:** Transkrypcja to najdłuższa czynność dla użytkownika. Wewnątrz mechanizmu transkrypcji siedziały delikatne obejścia (np. udawanie terminala przy pobieraniu modelu czy wklejanie łatek zgodności do tymczasowo tworzonych skryptów), a stare zgłoszenia `#3` i `#7` pokazały, że użytkownik musi od razu rozumieć, czy problemem jest sieć/zapora, brak modelu czy inny błąd.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Pobieranie modeli, budowanie podpowiedzi początkowych i uruchamianie skryptów tymczasowych siedzą razem w jednym dużym module. Zastąpienie sklejanych w locie plików czystymi, stałymi skryptami pomocniczymi otworzy bezpieczną drogę do nowych funkcji (np. rozpoznawania mówców lub nowszych modeli AI).

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 7 planu cementowania: Pobieranie modeli AI, bezpieczne uruchamianie transkrypcji (Windows/Linux/macOS) oraz strumieniowanie słów na żywo do edytora.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/engine/transcription.py
   - src/config/analysis_params.py (domyślne podpowiedzi i ustawienia AI)
   - src/handlers/analysis_worker.py
   - wywołania analizy i strumieniowania w src/engine/audio_engine.py oraz odbiór fragmentów na żywo w src/gui/main_window.py i src/gui/components/transcription_canvas.py
   - historyczne zgłoszenia GitHub #7, #3 i #19 (`gh issue view 7`, `gh issue view 3`) - sprawdź szczególnie, czy propozycja czytelnego komunikatu przy zablokowanym internecie/pobieraniu modelu ze zgłoszenia #7 została w pełni i wielojęzycznie wdrożona.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź działanie i spójność na Windows, Linux i macOS (pobieranie przy słabym internecie lub przerwaniu w połowie, ścieżki z polskimi znakami, równoległe przetwarzanie kawałków, zachowanie przycisku zatrzymania analizy, czyszczenie plików tymczasowych).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie kruche obejścia - typu udawanie okna konsoli czy sklejane w locie skrypty - tu działają i jaki realny problem użytkownika dziś łatają)?
   (B) Co obecnie może się psuć z perspektywy użytkownika (konkretne scenariusze: np. użytkownik za firmową zaporą lub z wolnym internetem klika Analizuj, pobiera model pierwszy raz i widzi zacięty pasek albo obcojęzyczny błąd zamiast jasnej instrukcji; albo wciska Zatrzymaj w połowie pobierania i zostaje uszkodzony model, który psuje kolejne próby)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz, co dokładnie zobaczy i zrobi użytkownik (przerwanie w połowie, brak sieci/miejsca na dysku, komunikaty podczas pobierania).

Po mojej akceptacji i wdrożeniu: napisz testy blokujące regresję (tests/ + run_tests.py), przetestuj na żywo uruchamianie potoku transkrypcji/anulowania i obsługę błędów sieci, wygeneruj i obejrzyj zrzuty ekranu okien pobierania/błędów, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 7 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 8. Wykrywanie powtórek, słów-wypełniaczy, fragmentów niezrozumiałych i ochrona ręcznych oznaczeń

- **Co obejmuje:** Czyszczenie typowych halucynacji Whispera, dzielenie strumienia słów na zdania i segmenty, samodzielne wykrywanie powtórzonych ujęć (dubli) i jąkań bez scenariusza, oznaczanie słów-wypełniaczy („yyy”, „eee”), wchłanianie niezrozumiałych przerw `(...)` w wycinane powtórki oraz ścisłą zasadę, że ręczne kliknięcie użytkownika jest zawsze ważniejsze niż podpowiedź algorytmu.
- **Dlaczego to ważne:** To główny „mózg” edycyjny BadWords. Jeśli algorytm nadpisze ręcznie pokolorowane słowo użytkownika albo zgubi dane projektu trzymane przy pierwszym słowie listy, kolejne etapy (podgląd cięć, montaż osi czasu) dostają błędne dane.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Algorytmy tekstowe są w jednym ponad 2-tysięcznym pliku, a odpalanie porównania w tle siedzi zagnieżdżone w środku silnika audio. Rozdzielenie reguł czyszczenia, wykrywania powtórek i porównywania ułatwi przyszłe ulepszanie wykrywania pomyłek bez ruszania reszty aplikacji.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 8 planu cementowania: Czyszczenie halucynacji AI, dzielenie na zdania, samodzielne wykrywanie powtórek i zacięć, automatyczne wypełniacze oraz nienaruszalność ręcznych oznaczeń użytkownika.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i testy:
   - src/algorithms.py (czyszczenie halucynacji, samodzielna analiza powtórek, wchłanianie niezrozumiałych fragmentów, reguła pierwszeństwa oznaczeń ręcznych, rozchodzenie się zmian)
   - metody budowania struktury słów i analizy w src/engine/audio_engine.py
   - testy w tests/test_algorithms.py i tests/test_data_contracts.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź poprawność działania na skrajnych przypadkach (puste nagrania, brak wykrytej mowy, bardzo długie powtórzenia, przełączanie filtrów po ręcznej edycji, nieangielskie znaki i interpunkcja).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (gdzie siedzą ukryte zasady kolejności warstw kolorów i pamięci pierwszego elementu listy - co dokładnie rozjechałoby się na montażu, gdyby ktoś to naruszył)?
   (B) Co obecnie może się psuć z perspektywy montażysty (konkretne przykłady zdań/nagrań: np. użytkownik ręcznie zostawia jedno „eee” bo pasuje do żartu, potem przestawia suwak albo filtr wypełniaczy i jego ręczna decyzja znika; albo lektor zacina się 3 razy na jednym zdaniu z przerwą `(...)` i wycięcie ucina początek właściwego zdania)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji podaj konkretny przykład na zdaniu, jak zachowa się tekst po kliknięciu użytkownika i zmianie automatu.

Po mojej akceptacji i wdrożeniu: rozbuduj testy w tests/ (run_tests.py) z prawdziwymi przypadkami zdań/powtórek/pustych nagrań, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 8 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 9. Wczytywanie scenariuszy (DOCX/PDF/TXT), porównanie ze scenariuszem i widok obok siebie (Side-by-Side)

- **Co obejmuje:** Wczytywanie scenariuszy z dysku lub wklejanie tekstu w panelu bocznym, wyciąganie specjalistycznych słów-kluczy ze scenariusza jako podpowiedzi dla AI, silnik porównujący nagrane słowa ze scenariuszem oraz okno/widok porównania linijka po linijce (Side-by-Side) ze skokiem do odpowiedniego miejsca na osi.
- **Dlaczego to ważne:** Porównywanie ze scenariuszem to jeden z największych wyróżników BadWords. W praktyce duże scenariusze lub nietypowo sformatowane pliki PDF/DOCX potrafią gubić polskie znaki, mylić dopasowanie przy długich dygresjach lub rozsynchronizować widok Side-by-Side względem głównego tekstu.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak - bardzo ważne dla przyszłości.** Silnik porównywania i budowanie widoku Side-by-Side są bardzo długie i ściśle powiązane z uruchamianiem skryptu pomocniczego z wnętrza silnika audio. Warto je wydzielić w czytelny sposób z myślą o otwartym zgłoszeniu **GitHub `#8`** (przyszła rozbudowa o nieliniowe dopasowanie scenariusza i pracę z wywiadami), ale **w tym etapie nie wdrażamy nowych funkcji z `#8`** - jedynie porządkujemy obecne porównywanie liniowe tak, by w przyszłości dało się łatwo dołożyć nowe tryby.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 9 planu cementowania: Obsługa plików scenariusza (DOCX/PDF/TXT), podpowiedzi trudnych słów dla AI, algorytm porównania ze scenariuszem oraz widok porównania obok siebie (Side-by-Side).

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te obszary:
   - wczytywanie DOCX/PDF, dopasowywanie ze scenariuszem i budowanie układu Side-by-Side w src/algorithms.py
   - wyciąganie trudnych słów i uruchamianie porównania w src/engine/audio_engine.py
   - src/gui/panels/script_panel.py
   - obsługa wczytywania skryptu, uruchamiania analizy porównawczej i widoku Side-by-Side w src/gui/main_window.py
   - zobacz też otwarte zgłoszenie GitHub #8 (`gh issue view 8`) wyłącznie jako kontekst przyszłego kierunku rozwoju - NIE wdrażaj teraz funkcji z #8 i NIE zamykaj #8; sprawdź tylko, czy obecne porządki ułatwią jego realizację w przyszłości.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź zachowanie na Windows, Linux i macOS (kodowanie polskich i międzynarodowych znaków w plikach TXT/PDF/DOCX, bardzo duże dokumenty, sytuacja gdy lektor przeczytał fragment w innej kolejności albo zaimprowizował długi blok).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie skróty albo osobne sposoby odpalania analizy scenariusza tu siedzą i dlaczego są - czy ułatwią przyszłe nieliniowe dopasowanie z `#8`)?
   (B) Co obecnie może się psuć w oczach użytkownika (konkretne scenariusze: np. użytkownik wrzuca scenariusz PDF z polskimi znakami i zamiast liter widzi krzaczki przez co nic się nie dopasowuje; lektor robi 2-minutową dygresję od scenariusza i widok Obok siebie zaczyna podświetlać złe linijki; albo duży scenariusz w DOCX wiesza okno na kilkanaście sekund)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji wyjaśnij, co zobaczy użytkownik w panelu scenariusza i widoku Obok siebie.

Po mojej akceptacji i wdrożeniu: napisz testy regresyjne (tests/ + run_tests.py) na realnych plikach DOCX/PDF/TXT z polskimi znakami, jeśli zmienisz widok Side-by-Side/panel scenariusza - wygeneruj i obejrzyj zrzuty ekranu, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 9 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

## Etap 3 (v4.3): Ekran powitalny, edytor, podgląd audio/wideo i okna ustawień

> Warstwa wizualna i codzienna wygoda montażu: bezpieczne odchudzenie głównego okna w 3 małych krokach, stabilny odtwarzacz z podglądem wideo i suwakami ciszy na żywo, szybki edytor tekstu (w tym rozwiązanie problemu zacinania na wielogodzinnych filmach z `#20`) oraz czyste ustawienia.

---

### 10A. Odchudzenie głównego okna (część 1): statystyki cięć, legenda kolorów, podgląd przekreśleń i eksport tekstu

- **Co obejmuje:** Wydzielenie z głównego okna (które ma ponad 5 tysięcy linijek) pierwszego dużego bloku niezwiązanego bezpośrednio z budową samego okna: przeliczania statystyk czasu i ciszy, odświeżania legendy kolorów i przełączników „Usuń”, wyliczania podglądu przekreśleń na tekście, szybkiego wycinania pojedynczym kolorem oraz eksportu i kopiowania czystego tekstu transkrypcji.
- **Dlaczego to ważne:** Ten blok wywołuje się przy niemal każdym kliknięciu na słowo w edytorze i bezpośrednio łączy się z powolnym działaniem na bardzo długich nagraniach (otwarte zgłoszenie GitHub `#20`). Wydzielenie go na zewnątrz pozwoli zmierzyć jego szybkość i łatwo go zoptymalizować w Punkcie 12B.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** To pierwsza z trzech bezpiecznych części rozbijania głównego okna na mniejsze, niezależne klocki bez zmiany działania widzianego przez użytkownika.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 10A planu cementowania: Wydzielenie z głównego okna przeliczania statystyk, legendy kolorów, podglądu przekreśleń cięć i eksportu tekstu (bez zmiany działania dla użytkownika).

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie tylko ten fragment projektu:
   - metody statystyk, legendy kolorów, podglądu cięć, wycinania koloru i eksportu/kopiowania tekstu w src/gui/main_window.py
   - src/gui/panels/colors_panel.py oraz src/gui/panels/assembly_panel.py
   - otwarte zgłoszenie GitHub #20 (`gh issue view 20`) - sprawdź, czy przeliczanie statystyk i legendy przy każdym kliknięciu słowa dokłada się do lagów na nagraniach 3-5+ godzinnych.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej elementami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź, gdzie statystyki i legenda są wywoływane z zewnątrz (np. panel ciszy, płótno transkrypcji, cofanie zmian, montaż) i jak zachowują się na długich projektach.
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (co ciężkiego wykonuje się dziś niepotrzebnie w oknie głównym przy pojedynczym kliknięciu słowa)?
   (B) Co obecnie może się psuć z perspektywy użytkownika (konkretne sytuacje: np. użytkownik ma 4-godzinny film, zaznacza jedno słowo i program przelicza cały tekst od zera powodując przycięcie; w panelu ciszy widzi inne minuty cięć niż w legendzie; albo eksportuje czysty tekst i dostaje wycięte już powtórki zamiast samej mowy)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz jasno, co zmienia się dla użytkownika w licznikach, legendzie i eksporcie tekstu.

Po mojej akceptacji i wdrożeniu: napisz testy dla liczników, legendy i eksportu tekstu (tests/ + run_tests.py + kontrola GUI), zweryfikuj na żywo spójność liczników przy klikaniu i cofaniu zmian, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 10A jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 10B. Odchudzenie głównego okna (część 2): paski boczne, skróty klawiszowe, obsługa zdarzeń i przyciski markerów

- **Co obejmuje:** Wydzielenie z głównego okna drugiego niezależnego bloku: zarządzania paskami bocznymi i zapamiętywania ich układu, przełączania ekranów (Powitanie / Przetwarzanie / Edytor), budowania przycisków wyboru kolorów markerów, zarządzania skrótami klawiszowymi (w tym blokowania skrótów podczas pisania w polach tekstowych) oraz trybu „Zawsze na wierzchu” / maksymalizacji.
- **Dlaczego to ważne:** Obsługa skrótów i pasków bocznych jest bardzo wrażliwa na kolejność kliknięć i różnice między Windows, Linux i macOS (np. kiedy piszesz nazwę pliku albo szukasz w tekście i naciśniesz klawisz koloru). Osobny, uporządkowany moduł od skrótów i układu okien da pewność, że nowe przyciski lub skróty nie zepsują pisania w polach tekstowych.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Drugi krok odchudzania głównego okna - pozwoli w przyszłości bez stresu dodawać nowe zakładki na pasku bocznym i nowe skróty.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 10B planu cementowania: Wydzielenie z głównego okna zarządzania paskami bocznymi, przełączania ekranów, przycisków markerów i skrótów klawiszowych.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie tylko ten fragment projektu:
   - metody pasków bocznych, przełączania aktywności, przycisków markerów, skrótów klawiszowych, filtrowania zdarzeń oraz przełączania stron w src/gui/main_window.py
   - src/gui/panels/main_workspace_panel.py, src/gui/views/editor_view.py, src/gui/views/processing_view.py
   - src/gui/dialogs/overlay.py (styk z globalnym przechwytywaniem kliknięć i klawisza Enter)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej elementami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność na Windows, Linux i macOS (skróty klawiszowe podczas pisania w wyszukiwarce lub polu scenariusza, zapamiętywanie układu pasków bocznych, kolejność rysowania przejść między ekranami).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie ręczne sztuczki przechwytujące klawisze i kliknięcia siedzą dziś w oknie głównym - co przestałoby działać na ekranie, gdyby je usunąć)?
   (B) Co obecnie może się psuć w codziennej pracy (konkretne scenariusze: np. użytkownik wpisuje szukane słowo w wyszukiwarce lub wkleja scenariusz i naciśnięcie litery albo Spacji niespodziewanie uruchamia skrót malowania lub włącza dźwięk; zamyka program z otwartym panelem bocznym i po restarcie układ nie wraca)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - dla każdego pytania wskaż dokładnie, jak skróty i paski mają reagować przy pisaniu i w oknach pomocniczych.

Po mojej akceptacji i wdrożeniu: napisz testy (tests/ + run_tests.py + kontrola GUI), przetestuj na żywo zdarzenia klawiszy i zapamiętywanie układu paneli w oknie Qt, zrób zrzuty ekranu układu edytora z paskami i sam je obejrzyj, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 10B jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 10C. Odchudzenie głównego okna (część 3): zadania w tle, sprawdzanie aktualizacji, komunikaty statusu i zamykanie

- **Co obejmuje:** Wydzielenie z głównego okna trzeciego, ostatniego bloku pomocniczego: uruchamiania i odbierania wyników zadań w tle (analiza, Szybka Cisza, wideo podglądu w tle, wczytywanie projektu w tle), obsługi tymczasowych komunikatów na górnej wyspie statusu, wywołania sprawdzenia telemetrii i aktualizacji po starcie oraz procedury bezpiecznego zamykania programu.
- **Dlaczego to ważne:** Gdy w jednym pliku mieszają się kliknięcia użytkownika z odbieraniem wyników pracy w tle i zamykaniem wątków przy wyjściu z programu, łatwo o zawieszenie lub błąd przy zamknięciu aplikacji podczas trwającej analizy albo tworzenia proxy.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Po tym punkcie główne okno stanie się lekkim szkieletem łączącym panele, dokładnie tak jak wymagają zasady projektu.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 10C planu cementowania: Wydzielenie z głównego okna obsługi zadań w tle, górnych komunikatów statusu, uruchamiania sprawdzeń po starcie oraz bezpiecznego zamykania aplikacji.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie tylko ten fragment projektu:
   - metody uruchamiania i zakończenia analizy, Szybkiej Ciszy, proxy w tle, wczytywania projektu w tle, komunikatów statusu, sprawdzania aktualizacji/telemetrii oraz zamykania w src/gui/main_window.py
   - src/handlers/analysis_worker.py
   - src/gui/components/top_status_island.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej elementami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (co się dzieje, gdy użytkownik zamknie okno podczas trwającej transkrypcji lub budowania podglądu wideo, czy blokada edytora podczas strumieniowania na żywo zawsze zdejmuje się po błędzie).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia przy przełączaniu zadań w tle, blokowaniu edycji czy okienkach po starcie tu siedzą)?
   (B) Co obecnie może się psuć z perspektywy użytkownika (konkretne scenariusze: np. użytkownik zamyka okno w trakcie analizy lub robienia proxy 360p - okno znika, a w tle dalej działa proces zjadający procesor i blokujący pliki; po nieudanej analizie edytor zostaje wyszarzony na stałe; albo na górnej wyspie nakładają się komunikaty)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz jasno zachowanie na ekranie (czy przy zamykaniu podczas analizy pytamy o przerwanie, w jakiej kolejności pojawiają się okienka po starcie).

Po mojej akceptacji i wdrożeniu: napisz testy (tests/ + run_tests.py + kontrola GUI), przetestuj na żywo cykl startu/anulowania/zamykania wątków w tle oraz wygeneruj i obejrzyj zrzuty ekranu górnej wyspy statusu, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 10C jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 11. Ekran powitalny: przełączanie źródła, kolejka plików lokalnych, wybór ścieżek i Szybka Cisza

- **Co obejmuje:** Pierwszy ekran po otwarciu BadWords: przełącznik między trybem DaVinci Resolve a trybem Plik lokalny, strefa przeciągnij-i-upuść z listą wielu plików i zmianą kolejności, wysuwana szuflada wyboru konkretnych ścieżek audio/wideo z osi czasu oraz przycisk szybkiego cięcia samej ciszy bez transkrypcji.
- **Dlaczego to ważne:** Na ekranie powitalnym użytkownik często zmienia tryby, odłącza lub podłącza DaVinci Resolve, wrzuca różne pliki wideo/audio z dysku lub odświeża osie czasu. W tych animowanych przejściach i kolejkach plików łatwo o przycięty układ okna, zapamiętanie nieistniejącej już ścieżki lub błędne zablokowanie trybu na komputerze bez Resolve.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Sposób, w jaki ekran powitalny komunikuje się z szufladą ścieżek i listą plików, jest silnie powiązany z oknem głównym. Warto go uporządkować, żeby w przyszłości łatwo było np. dodać obsługę zapisanych zestawów ustawień.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 11 planu cementowania: Ekran powitalny, wybór źródła (Plik lokalny vs Resolve), strefa upuszczania wielu plików, szuflada wyboru ścieżek oraz funkcja Szybka Cisza.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/views/welcome_view.py
   - src/gui/widgets/file_drop_zone.py
   - src/gui/components/track_options_drawer.py
   - obsługa ekranu powitalnego, wyboru osi/ścieżek i Szybkiej Ciszy w src/gui/main_window.py i src/engine/audio_engine.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (przeciąganie plików z eksploratora/Findera/menedżera plików, aktualne zasady DaVinci Resolve 21.1+ - gdzie wersja Free łączy się wyłącznie przez mostek Lua bez bezpośredniego Pythona, a wersja Studio pozwala na natywne połączenie, zachowanie bez zainstalowanego Resolve, płynność animacji zwijania i rozwijania).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (obejścia przy animacji szuflady ścieżek, rozpoznawaniu otwartego Resolve Free 21.1+ / Studio czy kolejce plików)?
   (B) Co obecnie może się psuć z punktu widzenia użytkownika (konkretne scenariusze: np. użytkownik darmowego Resolve 21.1+ włącza ekran powitalny przed uruchomieniem mostka Lua i widzi mylące komunikaty lub puste ścieżki; wrzuca do kolejki 2 filmy oraz nieobsługiwany dokument i nie dostaje jasnego sygnału; zmienia kolejność w kolejce lub wybiera Szybką Ciszę i szuflada przycina napisy)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz jasno reakcję na ekranie (duplikaty plików, mieszane rozdzielczości, brak otwartego mostka Resolve, Szybka Cisza).

Po mojej akceptacji i wdrożeniu: napisz testy (tests/ + run_tests.py), przetestuj na żywo przełączanie trybów i animację szuflady w oknie Qt, wygeneruj zrzuty ekranu obu trybów ekranu powitalnego i szuflady ścieżek i sam je obejrzyj, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 11 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 12A. Płótno transkrypcji: zaznaczanie ramką i tekstem, malowanie, przekreślenia, wyszukiwarka i Cofnij/Ponów

- **Co obejmuje:** Główny edytor tekstowy transkrypcji: układ ciągły i segmentowy, rysowanie ciągłego przekreślenia na wycinanych słowach, działanie lewego i prawego przycisku myszy (zaznaczanie jak w Notatniku, zaznaczanie prostokątną ramką, malowanie pędzlem), pływająca wyszukiwarka słów w tekście, własne markery oraz historia Cofnij / Ponów.
- **Dlaczego to ważne:** To tutaj użytkownik spędza 90% czasu. Z raportów w repozytorium wynika, że użytkownicy potrafią nie znaleźć przełącznika zaznaczania ramką albo trafić na drobne błędy przewijania, przycinania zaznaczeń przy szybkim ruchu myszą lub niepełnego cofania zmian w legendzie i statystykach po naciśnięciu Ctrl+Z.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Układanie słów na ekranie, obsługa myszki i rysowanie w jednym dużym pliku płótna są dość mocno splecione. Rozdzielenie samego liczenia pozycji słów od ich rysowania i obsługi kliknięć ułatwi w przyszłości np. obsługę etykiet mówców czy poprawianie literówek w słowach.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 12A planu cementowania: Płótno transkrypcji, tryby zaznaczania myszą (tekst, ramka, pędzel), przekreślenia cięć, wyszukiwarka w tekście, własne markery oraz Cofnij/Ponów.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/components/transcription_canvas.py
   - src/gui/components/search_overlay.py
   - src/handlers/undo_manager.py
   - src/gui/dialogs/marker_dialog.py
   - src/gui/dialogs/overlay.py (globalny filtr kliknięć i opóźnienie dymków)
   - połączenie edytora z legendą i skrótami w src/gui/main_window.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność na Windows, Linux i macOS (różnice w skrótach Ctrl vs Cmd na Macu, szybkie przewijanie kółkiem myszy i gładzikiem, klikanie podczas strumieniowania słów na żywo, intuicyjność przełączania trybów myszy).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia siedzą w rysowaniu przekreśleń, przeskoku z dymkami czy układaniu słów i co popsulibyśmy usuwając je bez planu)?
   (B) Co obecnie może się psuć z perspektywy użytkownika (konkretne przypadki z raportów i codziennej pracy: np. nowy użytkownik nie może znaleźć zaznaczania ramką; przy szybkim malowaniu myszą gubi słowa na zakrętach wiersza; klika Ctrl+Z i kolor słowa znika, ale odtwarzacz dalej przeskakuje to słowo; albo podczas strumieniowania na żywo klika słowo i edytor rozjeżdża zaznaczenie)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji wskaż wprost, jak rysuje się i zaznacza tekst pod kursorem użytkownika.

Po mojej akceptacji i wdrożeniu: napisz testy regresyjne (tests/ + run_tests.py), przetestuj na żywo operacje zaznaczania, szukania i Cofnij/Ponów w uruchomionym płótnie Qt, wygeneruj zrzuty ekranu edytora (w tym ramki, przekreśleń, wyszukiwarki i markerów) i sam je obejrzyj, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 12A jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 12B. Wydajność edycji i przeliczania cięć na wielogodzinnych nagraniach (zgłoszenie GitHub `#20`)

- **Co obejmuje:** Kompleksowe zbadanie i wyeliminowanie zacinania programu podczas zaznaczania słów (szczególnie na czerwono) przy bardzo długich filmach i podcastach trwających 3-5 godzin i więcej - zgodnie z otwartym zgłoszeniem na GitHubie (`#20`), gdzie przy 1 godzinie wszystko działa płynnie, a powyżej 3 godzin każde zaznaczenie słowa powoduje wyraźne przycięcie.
- **Dlaczego to ważne:** Przy kilkugodzinnym materiale transkrypcja ma dziesiątki tysięcy słów. Jeśli po zaznaczeniu choćby jednego słowa program za każdym razem od nowa układa cały dokument, przerysowuje całą falę dźwiękową, przelicza całą oś czasu i planuje zapis na dysk - interfejs zaczyna stawać na ułamek sekundy lub dłużej przy każdym ruchu myszą.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Wymaga wyraźnego oddzielenia lekkiego odświeżenia samego widocznego fragmentu ekranu od ciężkiego pełnego przeliczania całego projektu, aby przyszłe funkcje edytora także działały błyskawicznie nawet przy 8-godzinnych transmisjach.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 12B planu cementowania: Wydajność zaznaczania i malowania słów oraz przeliczania podglądu cięć przy wielogodzinnych nagraniach (otwarte zgłoszenie GitHub #20).

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Najpierw przeczytaj dokładnie zgłoszenie GitHub #20 (`gh issue view 20`), a potem prześledź cały łańcuch zdarzeń od kliknięcia / pomalowania słowa na czerwono aż po koniec odświeżenia ekranu w tych plikach:
   - src/gui/components/transcription_canvas.py (przeliczanie układu i odświeżanie po zmianie koloru słowa)
   - wywołania odświeżania podglądu cięć, statystyk i legendy kolorów w src/gui/main_window.py (lub wydzielonym module z Punktu 10A)
   - src/engine/audio_engine.py (przeliczanie cięć osi czasu wywoływane w trakcie edycji)
   - src/gui/components/waveform_timeline.py oraz src/gui/components/audio_preview.py (reakcja wykresu fali i odtwarzacza na zmianę koloru słowa)
   - src/handlers/autosave_manager.py (czy przy każdym słowie nie kopiuje się w pamięci dziesiątek tysięcy słów)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku w tym łańcuchu reakcji (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Zmierz realnie (na żywo w pamięci / oknie Qt na wygenerowanym 5-godzinnym projekcie z dziesiątkami tysięcy słów) czas reakcji dla 1 godziny vs 5 godzin na pojedyncze zaznaczenie i szybkie malowanie myszą.
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co w tym łańcuchu odświeżania wygląda dziwnie lub nadmiarowo (dlaczego przy kliknięciu jednego słowa program wykonuje ciężką pracę jak dla całego filmu)?
   (B) Co dokładnie odczuwa użytkownik ze zgłoszenia #20 (opisz krok po kroku: ile milisekund/sekund stoi ekran przy kliknięciu słowa na 5-godzinnym podcaście, co dzieje się przy przeciąganiu pędzlem i jakie inne miejsca także przytną program przy długim nagraniu)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji podaj odczuwalną dla użytkownika różnicę (np. czy przy malowaniu statystyki i wykres fali odświeżają się natychmiast po puszczeniu przycisku myszy z opóźnieniem 50-100 ms, a samo słowo podświetla się w ułamku milisekundy).

Po mojej akceptacji i wdrożeniu:
- napisz i uruchom realny test wydajnościowy na żywo na zestawie słów odpowiadającym 5 godzinom mowy (zmierz dokładny czas przed i po) oraz uruchom run_tests.py,
- wygeneruj zrzuty ekranu i obejrzyj je samodzielnie, aby potwierdzić, że przekreślenia, legenda i wykres fali odświeżają się bezbłędnie,
- zamknij zgłoszenie #20 na GitHubie przez `gh issue close 20` z krótkim podaniem przyczyny i naprawy,
- wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 12B jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 13. Dolny odtwarzacz audio/wideo, omijanie cięć w czasie rzeczywistym i regulacja głośności

- **Co obejmuje:** Dolny dok odtwarzania: przyciski Play/Stop/Przewijanie, suwak czasu, szybkość odtwarzania, zwijanie i rozwijanie panelu, dynamiczne omijanie wyciętych słów i ciszy w locie („Skip Cuts”), głośność oraz automatyczne pobieranie brakującego dźwięku z Resolve po wczytaniu starego projektu.
- **Dlaczego to ważne:** Testerzy zgłaszali kłopoty z niedziałającymi przyciskami odtwarzacza oraz ostrzeżenia o stylach czcionek w tym panelu. Dodatkowo odtwarzacz zawiera osobne obejście do sterowania głośnością na Linuksie (poprzez systemowy mikser dźwięku) oraz sztuczkę wyciszania przy przeskoku, żeby uniknąć trzasków w słuchawkach - wszystko to musi działać gładko na każdym systemie.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Odtwarzacz łączy w sobie sterowanie oknem, logikę przeskakiwania wycięć, podgląd wideo i dogrywanie brakującego dźwięku w jednym rozbudowanym pliku. Wydzielenie logiki omijania cięć i synchronizacji ze słowami do osobnej małej części zapobiegnie błędom rozsynchronizowania przy przyszłych zmianach odtwarzacza.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 13 planu cementowania: Dolny odtwarzacz audio/wideo, automatyczne omijanie wyciętych fragmentów na żywo, głośność między systemami oraz dogrywanie brakującego audio.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/components/audio_preview.py
   - src/gui/components/video_preview.py
   - src/gui/widgets/sliders.py
   - przygotowanie pliku audio do podglądu w src/engine/audio_extraction.py
   - powiązania odtwarzacza z edytorem i oknem głównym w src/gui/main_window.py
   - raport/raport.md (zgłoszenie testera o problemach z odtwarzaczem)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (różne silniki multimedialne, regulacja głośności na Linuksie bez systemowego miksera, płynność przeskoku nad wieloma krótkimi wycięciami bez trzasków, synchronizacja czasu i podświetlanego słowa, a także skok głowicy na osi DaVinci Resolve z uwzględnieniem mostka Lua w darmowym Resolve 21.1+ vs Studio).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia dla głośności na Linuksie, wyciszania trzasków przy skoku czy dogrywania brakującego audio ze starego projektu tu siedzą)?
   (B) Co obecnie może się psuć w oczach użytkownika (konkretne sytuacje z raportu testera i codziennego montażu: np. użytkownik klika Play/Pauza w dolnym pasku i nic się nie dzieje; włącza prędkość 1.5x/2x z omijaniem cięć i podświetlane słowo rozjeżdża się z głosem albo słychać trzask w słuchawkach przy serii powtórek; wczytuje stary projekt bez dźwięku podglądu i odtwarzacz milczy bez wskazówki)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz, co użytkownik usłyszy i zobaczy po kliknięciu Play, kliknięciu wyciętego słowa i dojściu do końca nagrania.

Po mojej akceptacji i wdrożeniu: napisz testy dla przedziałów pomijania i czasu (tests/ + run_tests.py), przetestuj na żywo sterowanie dolnym odtwarzaczem i logikę omijania cięć, wygeneruj i obejrzyj zrzuty ekranu odtwarzacza (zwinięty/rozwinięty/podgląd wideo), wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 13 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 14. Wykres fali dźwiękowej, podgląd wideo 360p (proxy) oraz suwaki ciszy na żywo

- **Co obejmuje:** Tworzenie i zapamiętywanie w pamięci podręcznej wykresu fali dźwiękowej, rysowanie zielonej wstęgi klipów z kreskowanymi strefami cięć, przybliżanie i przewijanie osi podglądu, generowanie lekkiego wideo 360p w tle (zarówno z plików lokalnych, jak i z osi Resolve) oraz natychmiastowe przeliczanie statystyk i cięć ciszy przy przesuwaniu suwaków w panelu Cisza.
- **Dlaczego to ważne:** Te elementy tworzą wrażenie płynnej pracy w czasie rzeczywistym („jak w dużym programie montażowym”). Jeśli wyliczenia wykresu fali albo kolejność przycięcia wideo proxy z kilku klipów rozjadą się z wyliczeniem cięć, użytkownik zobaczy na podglądzie inne miejsce niż to, co wytnie montaż końcowy.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Przeliczanie statystyk cięć na żywo jest rozrzucone między panelem ciszy a oknem głównym, a tworzenie proxy 360p ma własne gałęzie doboru kodeków dla kart graficznych i procesorów. Uporządkowanie tego w jedno wspólne miejsce da pewność, że przyszłe ulepszenia osi podglądu nie rozjadą się z montażem.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 14 planu cementowania: Wykres fali dźwiękowej, podgląd wideo 360p w tle oraz przeliczanie cięć ciszy na żywo przy przesuwaniu suwaków.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/engine/waveform.py
   - src/gui/components/waveform_timeline.py
   - src/gui/panels/silence_panel.py
   - generowanie podglądu wideo 360p i dostrajanie przedziałów ciszy w src/engine/audio_engine.py oraz src/handlers/analysis_worker.py
   - uruchamianie przeliczania ciszy i proxy w tle w src/gui/main_window.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność na Windows, Linux i macOS (sprzętowe vs programowe tworzenie wideo 360p, płynność przy wielokrotnym przesuwaniu suwaków ciszy, synchronizacja przybliżenia fali z podglądem cięć i wieloma klipami oraz tworzenie podglądu z osi DaVinci Resolve w tym Free 21.1+ przez mostek Lua).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia przy wyborze kodeka karty graficznej do proxy 360p, pamięci podręcznej wykresu fali czy płynnym wygaszaniu statystyk są zastosowane)?
   (B) Co obecnie może się psuć w oczach użytkownika (konkretne scenariusze: np. użytkownik na starszej karcie graficznej otwiera projekt i w tle cicho wysypuje się podgląd wideo 360p; przybliża falę dźwiękową kółkiem i kliknięcie na fali przenosi w inne miejsce niż zaznaczona kreska; albo na godzinnym wywiadzie przesuwa suwak ciszy i wskaźniki zaczną skakać lub zatykają pamięć)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji wskaż wprost, co zmieni się na ekranie przy kolejce filmów o różnych proporcjach i przy zoomie fali.

Po mojej akceptacji i wdrożeniu: napisz testy regresyjne (tests/ + run_tests.py), przetestuj na żywo generowanie fali/proxy i reakcję suwaków ciszy, zrób zrzuty ekranu wykresu fali oraz panelu ciszy i sam je obejrzyj, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 14 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 15. Okno Ustawień i biblioteka własnych kontrolek interfejsu

- **Co obejmuje:** Okno Ustawień (wyszukiwarka opcji, tryb Podstawowy vs Zaawansowany, płynne przyciemnianie opcji XML/DRT, zakładki, eksport/import ustawień, przywracanie domyślnych) oraz biblioteka własnych kontrolek (przełączniki, listy rozwijane z przewijanym długim tekstem, przyciski nagrywania skrótów myszy i klawiatury, przycisk dzielony Assemble).
- **Dlaczego to ważne:** Okno Ustawień ma ponad 3,3 tys. linijek, a zbiór własnych przycisków ponad 2,7 tys. linijek - i niemal każdy ekran aplikacji z nich korzysta! Jedna zmiana w liście rozwijanej czy przycisku potrafi popsuć wygląd wielu okien naraz, a w samych ustawieniach siedzą wbudowane kopie logiki aktualizacji i zgłaszania błędów.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Zarówno okno Ustawień, jak i plik z przyciskami przydałoby się rozbić na mniejsze, tematyczne części, zachowując pełną wsteczną zgodność, aby łatwo dodawać nowe ustawienia w przyszłości.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 15 planu cementowania: Okno Ustawień oraz wspólne własne kontrolki interfejsu (przyciski, przełączniki, listy rozwijane, przechwytywanie skrótów).

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/dialogs/settings_dialog.py
   - src/gui/widgets/buttons.py
   - src/gui/widgets/delegates.py
   - src/gui/widgets/labels.py
   - src/gui/widgets/language_selector.py
   - src/gui/widgets/layouts.py i splitters.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność na Windows, Linux i macOS (listy rozwijane w oknach bez ramki, skalowanie 75%-150%, wyszukiwarka ustawień, rozpoznawanie trybów myszki niezależnie od języka UI, skróty Cmd na macOS oraz poprawne blokowanie opcji DRT w zakładce DaVinci Resolve dla darmowej wersji 21.1+ z aktualną dokumentacją).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (dlaczego w oknie Ustawień zostały obejścia przy przełączaniu języka na żywo, sprawdzaniu nazw opcji po przetłumaczonym tekście czy kawałku starej logiki aktualizacji)?
   (B) Co obecnie może się psuć z perspektywy użytkownika (konkretne sytuacje: np. użytkownik na Linuksie lub macOS otwiera listę rozwijaną i lista chowa się za oknem; zmienia 3 ustawienia i klika Anuluj, a mimo to część zmian zostaje albo przy wyszukiwaniu opcji zaawansowanej nie widzi wyniku; ustawia skrót na Macu i zamiast Cmd dostaje dziwny symbol)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji napisz wyraźnie, co zobaczy i odczuje użytkownik po kliknięciu Zapisz, Anuluj czy wpisaniu hasła w wyszukiwarkę.

Po mojej akceptacji i wdrożeniu: rozbuduj testy w tests/test_settings_and_version.py (uruchom run_tests.py), przetestuj na żywo otwieranie zakładek, wyszukiwarkę, przełącznik XML/DRT i animację przyciemniania, wygeneruj i obejrzyj zrzuty ekranu wszystkich zmienionych zakładek i kontrolek, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 15 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

## Etap 4 (v4.4): DaVinci Resolve, montaż osi czasu, eksport i zapis projektów

> Kluczowe wyjście produktu: niezawodna łączność z każdą wersją DaVinci Resolve, dokładne co do klatki składanie osi czasu i eksport do innych programów, oraz bezpieczne zapisywanie pracy użytkownika.

---

### 16. Łączność z DaVinci Resolve, mostek dla darmowej wersji 21.1+ i praca całkowicie bez Resolve

- **Co obejmuje:** Automatyczne wykrywanie wersji i edycji DaVinci Resolve (Free przed 21.1, Free 21.1+, Studio, wersja z Mac App Store), wdrażanie skryptów startowych do Resolve, działanie mostka komunikacyjnego (skrypt Lua + skrzynka wymiany plików) dla zablokowanego darmowego Resolve 21.1+ (zgłoszenie `#5`), płynne kolejkowanie skoków odtwarzacza oraz czyste działanie w trybie samodzielnym bez zainstalowanego Resolve.
- **Dlaczego to ważne:** To najbardziej wrażliwy na zmiany zewnętrzne element aplikacji (aktualizacje DaVinci Resolve potrafią zmieniać blokady i ścieżki). Sam moduł obsługi Resolve ma ponad 3,7 tys. linijek i obsługuje dwa różne sposoby komunikacji (bezpośredni i przez mostek Lua) z osobnymi obejściami dla Windows, macOS i Linuksa.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Moduł łącznika z Resolve trzyma naraz obsługę połączenia, czytanie osi czasu, renderowanie dźwięku i wideo, a nawet ręczne składanie XML na osi. Rozdzielenie samej komunikacji (bezpośrednia vs mostek Lua) od operacji na osiach ułatwi w przyszłości dodanie np. integracji z innymi programami montażowymi.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 16 planu cementowania: Wykrywanie i łączność z DaVinci Resolve, mostek Lua dla darmowej wersji 21.1+ oraz pełna izolacja w trybie bez Resolve.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/api/resolve_handler.py
   - src/api/resolve_bridge.py
   - setupfiles/BadWords Bridge.lua
   - wykrywanie i wdrażanie skryptów Resolve w src/osdoc.py oraz sprawdzenie wywołań w installer/src/engine.rs
   - testy odizolowania od Resolve w tests/test_host_env_fixes.py
   - historyczne zgłoszenie GitHub #5 (`gh issue view 5`) oraz sprawdź otwarte zgłoszenia (`gh issue list --state open`), czy pojawiły się nowe problemy z łącznością Resolve.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów; sprawdź też, czy w src/bridge/ nie zostały jakieś puste/stare ślady).
3. Sprawdź OBOWIĄZKOWO aktualną dokumentację oraz najświeższe zmiany DaVinci Resolve (21.1+, 21.2+, 22+ - lokalne README SDK jeśli jest na dysku oraz aktualne informacje z sieci) oraz spójność między Windows, Linux i macOS (w tym brak Python API i zewnętrznego socketa w darmowym Resolve 21.1+, ograniczenia piaskownicy Lua bez io/ffi/require, współdzielona paczka na macOS dla Free/Studio i wersja z Mac App Store, polskie znaki między Lua a Pythonem, jednoczesny dostęp do pliku na Windowsie).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (dlaczego w darmowym Resolve 21.1+ potrzebny jest cały mechanizm skrzynki Lua i odczyt współdzielony na Windowsie - opisz, co użytkownik zobaczyłby na ekranie bez tych obejść)?
   (B) Co obecnie może się psuć w oczach użytkownika (konkretne scenariusze: np. użytkownik zaktualizował darmowe Resolve do 21.1+/22, w menu ma i BadWords i BadWords Bridge i nie wie co kliknąć; albo podczas długiego renderowania/skoku na osi traci połączenie z mostkiem; na Macu program błędnie zgaduje wersję Free dla Studio i omija szybkie połączenie; albo nazwy klipów z polskimi znakami zniekształcają się w komunikacji)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz jasno doświadczenie użytkownika (co widzi w menu, jakie okienko podpowiada uruchomienie mostka, co robi program gdy Resolve zostanie zamknięte w trakcie pracy).

Po mojej akceptacji i wdrożeniu: napisz testy symulujące wszystkie tryby (brak Resolve, Free 21.1+, Studio) oraz przetestuj na żywo komunikację mostka (prawdziwy zapis/odczyt pliku request.lua i odpowiedź w stylu Fusion.prefs), wygeneruj i obejrzyj zrzuty ekranu ewentualnych komunikatów połączenia, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 16 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 17. Dokładność klatkowa i montaż osi czasu w DaVinci Resolve (XML vs natywny DRT)

- **Co obejmuje:** Przeliczanie oznaczonych wycięć na dokładne przedziały co do klatki (w tym ułamkowe klatkaże 23.976, 29.97, 59.94), składanie nowej osi czasu w Resolve domyślną metodą XML (utrzymującą złączone audio i wideo), alternatywną metodą natywnego pliku DRT (dla zachowania kolorów i efektów w Studio), przenoszenie kolorowych markerów na oś czasu oraz bezpieczne sprzątanie duplikatów w Media Pool.
- **Dlaczego to ważne:** Tutaj każda pomyłka o jedną klatkę albo zły punkt startowy z metadanych nagrania (Broadcast Wave) potrafi rozsynchronizować dźwięk z obrazem pod koniec długiego filmu albo rozciąć niewłaściwy klip na wielościeżkowej osi czasu.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Logika składania osi czasu w Resolve jest rozrzucona między modułem montażowym, silnikiem audio a końcówką dużego pliku łącznika z Resolve. Zgromadzenie matematyki klatek i reguł składania osi w jednym, czystym miejscu zabezpieczy przed rozjazdem między trybami XML i DRT.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 17 planu cementowania: Matematyka klatkowa oraz montaż osi czasu w DaVinci Resolve (tryb XML vs tryb DRT, wielościeżkowość, markery, łączenie audio-wideo i Media Pool).

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i testy:
   - src/assembler.py (część DRT, czyszczenie Media Pool, dokładne wyliczanie klatkaży i metadanych startowych)
   - obliczanie operacji cięć i uruchamianie montażu w src/engine/audio_engine.py
   - budowanie i importowanie osi czasu przez XML w src/api/resolve_handler.py
   - src/gui/panels/assembly_panel.py oraz panel legendy i montażu w src/gui/main_window.py
   - testy w tests/test_timeline_cuts.py i tests/test_assembler_xml.py
   - raport/raport.md (uwaga o rozjechanych cięciach na osi subframowej)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Zweryfikuj aktualną dokumentację DaVinci Resolve 21.1+ / 22+ (wymuszone ominięcie DRT na korzyść XML w darmowym Resolve 21.1+, ograniczenia ImportTimelineFromFile dla DRT vs XML) oraz sprawdź spójność między Windows, Linux i macOS dla skrajnych osi czasu (ułamkowe klatkaże 23.976/29.97/59.94, przesunięcia kodu czasowego np. 01:00:00:00, wiele ścieżek audio i wideo, klipy złożone / napisy / przejścia, polskie znaki w nazwach klipów).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia przy łataniu plików DRT, ukrywaniu migotania Resolve przy imporcie czy sprzątaniu Media Pool są używane i co zepsułoby się w montażu użytkownika bez nich)?
   (B) Co obecnie może się psuć w gotowym montażu użytkownika (konkretne scenariusze z raportów i praktyki: np. użytkownik montuje godzinny wywiad 29.97 fps i pod koniec filmu dźwięk wyprzedza ruch ust; w darmowym Resolve 21.1+ czeka 30 sekund zanim program przejdzie z DRT na XML; na wielościeżkowej osi znika lub przycina mu ścieżkę z muzyką w tle; albo po montażu w Media Pool zostają dziesiątki zduplikowanych klipów)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji wyjaśnij dokładnie, jak będzie wyglądać zmontowana oś czasu w DaVinci Resolve (puste luki, ścieżki z muzyką, klipy złożone, markery).

Po mojej akceptacji i wdrożeniu: rozbuduj testy dokładności klatkowej i wygenerowanych osi (tests/ + run_tests.py), zweryfikuj na żywo strukturę realnie wygenerowanych plików XML/DRT i przejść na osi czasu, jeśli zmienisz panel montażu - wygeneruj i obejrzyj zrzuty ekranu, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 17 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 18. Eksport dla innych programów montażowych w trybie niezależnym (XML, FCPXML, OTIO, EDL i cięcie pliku)

- **Co obejmuje:** Okno eksportu w trybie bez DaVinci Resolve: wykrywanie domyślnego klatkażu i rozdzielczości wrzuconych plików, generowanie osi czasu dla Premiere Pro, Final Cut Pro, Resolve i innych programów (FCP7 XML, FCPXML, OTIO, EDL) wskazujących zawsze oryginalne pliki (nigdy lekkie wideo podglądu 360p) oraz opcjonalne bezpośrednie wycinanie do gotowego pliku audio/wideo bez programu montażowego.
- **Dlaczego to ważne:** Tryb niezależny to główna nowość wersji 4.0. Każdy z tych formatów ma własne wymagania dotyczące ścieżek dyskowych, czasu startowego nagrania i zgodności z innymi programami montażowymi (szczególnie na Windowsie vs macOS ze względu na format adresów plików). Dodatkowo w oknie eksportu została awaryjna emotka tekstu i powielony mechanizm podpowiedzi „(i)”.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Cztery różne formaty eksportu w jednym długim pliku dzielą wspólną logikę klatek i czasu startowego, którą warto wyraźnie ujednolicić, aby dodanie w przyszłości kolejnego formatu eksportu (np. napisów SRT) było proste i bez powielania obliczeń.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 18 planu cementowania: Eksport w trybie samodzielnym (FCP7 XML, FCPXML, OTIO, EDL), bezpośrednie cięcie pliku medialnego oraz okno dialogowe eksportu.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/dialogs/export_dialog.py
   - generatory formatów FCP7 XML, OTIO, FCPXML, EDL oraz bezpośrednie cięcie bezstratne/FFmpeg w src/assembler.py
   - przygotowanie przepisu cięcia i wykonanie w src/engine/audio_engine.py
   - wywołanie okna eksportu i montażu w trybie plikowym w src/gui/main_window.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS oraz zgodność wygenerowanych plików z aktualnym DaVinci Resolve 21.1+, Premiere Pro i Final Cut Pro (ścieżki ze spacjami, polskimi znakami i literami dysków Windowsa, wieloklipowa kolejka o różnych parametrach, przypadek braku biblioteki OTIO).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (dlaczego w formatach eksportu są obejścia ścieżek, powielone fragmenty podpowiedzi czy zapasowa emotka w oknie eksportu - i gdzie na ekranie widać te pozostałości)?
   (B) Co obecnie może się psuć dla użytkownika (konkretne scenariusze: np. użytkownik na Windowsie eksportuje montaż z folderu o polskiej nazwie, otwiera XML w DaVinci Resolve albo Premiere i program widzi „Media Offline” lub co gorsza podpina lekkie wideo podglądu 360p zamiast oryginału; albo wrzuca klipy 30 fps i 60 fps do kolejki i bezpośrednie cięcie wywala się w połowie)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji wskaż wprost, co zobaczy użytkownik w oknie eksportu i co otworzy potem w swoim programie montażowym.

Po mojej akceptacji i wdrożeniu: napisz testy dla wszystkich formatów (XML, FCPXML, OTIO, EDL) w tests/ + run_tests.py, przetestuj na żywo generowanie realnych plików eksportu i cięcie FFmpeg na próbce wideo, wygeneruj i obejrzyj zrzuty ekranu okna eksportu, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 18 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 19. Zapis projektu (`.bws`), autozapis, odzyskiwanie po awarii i okno niezapisanych zmian

- **Co obejmuje:** Zapisywanie i otwieranie plików projektu BadWords (`.bws` zawierających transkrypcję, kolory, ustawienia i opcjonalnie zapakowane audio lub kopię osi), działanie automatycznego zapisu w tle, odtwarzanie sesji po niespodziewanym zamknięciu programu oraz pytanie o niezapisane zmiany przy zamykaniu lub czyszczeniu projektu.
- **Dlaczego to ważne:** Użytkownik po godzinie pracy nad montażem absolutnie nie może stracić oznaczonych cięć przy awarii prądu albo przypadkowym zamknięciu. Z drugiej strony przestarzałe pliki autozapisu albo zbyt wolne wczytywanie wielkich projektów z dysku potrafią zablokować ekran albo pytać o odzyskanie już po zwykłym, czystym zamknięciu aplikacji.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Otwieranie i zapisywanie projektu wisi w trzech miejscach naraz (menedżer autozapisu, moduł preferencji i spory fragment okna głównego do wczytywania w tle). Zebranie formatu projektu `.bws` i reguł „czy projekt ma niezapisane zmiany” w jednym czystym miejscu ułatwi dodawanie kolejnych informacji do pliku projektu w przyszłości.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 19 planu cementowania: Zapis i otwieranie projektów (.bws), autozapis w tle, odzyskiwanie po awarii oraz wykrywanie niezapisanych zmian.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/engine/preferences.py (zapis/odczyt stanu projektu i archiwów .bws)
   - src/handlers/autosave_manager.py
   - src/gui/dialogs/unsaved_changes_dialog.py
   - obsługa eksportu/importu projektu, wątku wczytywania, sprawdzania odzyskiwania po starcie oraz zamykania w src/gui/main_window.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (duże archiwa `.bws` z osadzonym audio, bezpieczne atomowe zapisywanie żeby awaria prądu w połowie nie zniszczyła starego pliku, przenoszenie `.bws` na inny komputer, działanie w trybie lokalnym vs w Resolve - w tym zapasowe `source.xml` dla darmowego Resolve 21.1+ zamiast DRT).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (jakie skróty siedzą przy pakowaniu plików `.bws`, rozpoznawaniu czystego zamknięcia programu czy ratowaniu osi z darmowego Resolve 21.1+)?
   (B) Co obecnie może się psuć w oczach użytkownika (konkretne scenariusze: np. użytkownik kończy godzinny montaż, zamyka czysto program, otwiera następnego dnia i znów dostaje pytanie o odzyskanie starej sesji; albo pokolorował 50 słów, zamyka krzyżykiem i program nie ostrzega przed utratą zmian; albo wysyła `.bws` koledze na inny komputer i po otwarciu program nie potrafi odnaleźć wideo)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz jasno, kiedy program zapyta o zapis, co trafi do `.bws` i kiedy pokaże okno odzyskiwania.

Po mojej akceptacji i wdrożeniu: napisz testy zapisu/odczytu/odzyskiwania (tests/ + run_tests.py), przetestuj na żywo pełny zapis, rozpakowanie i symulację nagłego przerwania na realnym pliku `.bws`, wygeneruj i obejrzyj zrzuty ekranu okna niezapisanych zmian oraz odzyskiwania sesji, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 19 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

## Etap 5 (v4.5): Instalator, aktualizacje, zgłaszanie błędów i sprzątanie

> Pierwsze wrażenie i długowieczność programu: niezawodna instalacja na czystym komputerze, jedna prosta ścieżka aktualizacji bez duplikatów, uczciwa telemetria i bezbolesne zgłaszanie błędów.

---

### 20. Nowoczesny instalator, uruchamiacze (launchery) i porządek ze starym instalatorem

- **Co obejmuje:** Cała ścieżka instalacji, naprawy, przenoszenia, resetowania i odinstalowywania BadWords na Windowsie, Linuksie i macOS: skrypty startowe wklejane do terminala, graficzny/terminalowy instalator w Rust, pobieranie FFmpeg i Pythona, budowanie skrótów systemowych i własnych uruchamiaczy aplikacji (w tym obsługa spacji i znaków narodowych w ścieżkach ze zgłoszenia `#18`) oraz relacja do ogromnego starego instalatora w Pythonie, który wciąż leży w repozytorium.
- **Dlaczego to ważne:** Obecnie w repozytorium istnieją równolegle **dwa** ponad 4-tysięczne systemy instalacyjne (nowy w Rust oraz stary w Pythonie). Utrzymywanie dwóch niezależnych kopii tej samej logiki powoduje rozjazdy, jak choćby problemy z pobieraniem FFmpeg na macOS lub różne zachowanie przy przenoszeniu folderu.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Wymaga jasnej decyzji, czy stary instalator w Pythonie jest jeszcze w ogóle potrzebny jako zapas, czy można go bezpiecznie wycofać/zarchiwizować, a sam kod instalatora w Rust podzielić na mniejsze, czytelne części.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 20 planu cementowania: Proces instalacji, naprawy, przenoszenia i odinstalowania BadWords, uruchamiacze aplikacji oraz kwestia współistnienia nowego instalatora i starego skryptu instalacyjnego.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te obszary:
   - installer/src/ (main.rs, engine.rs, state.rs, dialogs.rs, i18n.rs, os/windows.rs, os/linux.rs, os/macos.rs, os/mod.rs)
   - setupfiles/setup.py (sprawdź, kto i kiedy jeszcze z niego korzysta!)
   - skrypty rozruchowe: setupfiles/windows-setup.ps1, setupfiles/linux-setup.sh, setupfiles/mac-setup.sh
   - natywne uruchamiacze i ikony: setupfiles/windows/, setupfiles/linux/, setupfiles/macos/, setupfiles/pe_patcher.py
   - raport/logi_macOS_prawdopodobnie_blad_pobierania_ffmpega.log oraz zgłoszenie GitHub #18 (`gh issue view 18` - uruchamianie `BadWords.exe` i błąd ścieżki)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (zwłaszcza w .github/workflows/, README.md i src/ - nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (blokady SmartScreen/Smart App Control i Apple Gatekeeper, zamykanie okna terminala po uruchomieniu instalatora, pobieranie FFmpeg na wszystkie architektury w tym Apple Silicon, wdrażanie skryptów do aktualnego DaVinci Resolve 21.1+ - `BadWords Bridge.lua` + nieszkodliwe `BadWords.py` przy współdzielonej paczce na macOS, skróty na pulpicie/w menu oraz bezpieczne usuwanie bez kasowania cudzych folderów).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (dlaczego w repozytorium nadal siedzą dwa osobne instalatory, ręczne łaty programów startowych czy ścieżki awaryjne i czy usunięcie starego instalatora komukolwiek dziś zaszkodzi)?
   (B) Co obecnie może się psuć dla nowego użytkownika (konkretne scenariusze: np. użytkownik na Macu odpala instalator i dostaje błąd pobierania FFmpeg z logów; na Linuksie wkleja komendę z README i zostaje wiszące czarne okno terminala; po aktualizacji ze starej wersji v3 skrót nadal odpala popsute ścieżki; albo instalator w Rust robi coś inaczej niż sam program przy wykrywaniu Resolve 21.1+)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji wskaż konkretną różnicę w doświadczeniu instalującego użytkownika (stary instalator, przenoszenie folderu, pobieranie Pythona).

Po mojej akceptacji i wdrożeniu: sprawdź budowanie i testy instalatora (`cargo check && cargo test` w installer/ + `run_tests.py`), przetestuj na żywo działanie binarnego instalatora/uruchamiaczy na bezpiecznym folderze testowym (i sprawdź wizualnie okno instalatora na zrzucie ekranu jeśli zmienisz GUI), wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 20 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 21. Jedna, spójna ścieżka aktualizacji aplikacji i usunięcie powielonych skryptów

- **Co obejmuje:** Cały mechanizm sprawdzania nowych wersji i aktualizowania BadWords: ciche aktualizacje w tle z okna głównego i przy starcie, ręczne aktualizowanie z okna powiadomienia o nowej wersji, osobny przycisk aktualizacji w karcie Ustawień, okno informacji po przejściu z wersji 3.x na 4.0, a także sprawdzenie powielonych skryptów aktualizacji leżących w kilku różnych folderach repozytorium.
- **Dlaczego to ważne:** W tej chwili ścieżka aktualizacji jest rozproszona po aż 5 miejscach w aplikacji i przynajmniej 3 miejscach wśród skryptów aktualizacji (w głównym folderze skryptów, w podfolderze ze starszymi plikami oraz w osobnym folderze aktualizatorów). Taki układ bardzo łatwo prowadzi do sytuacji z raportu testera, gdzie aktualizacja ze starszej wersji zostawiła zepsute środowisko lub stare pliki.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Sprowadzenie pobierania i odpalania aktualizacji do jednego wspólnego mechanizmu (zamiast osobnych kopii przy starcie, w oknie aktualizacji i w oknie Ustawień) radykalnie zmniejszy ryzyko zepsucia działania po wydaniu kolejnej wersji.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 21 planu cementowania: Ujednolicenie całego systemu aktualizacji aplikacji oraz posprzątanie powielonych skryptów aktualizujących.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i foldery:
   - setupfiles/updater.py
   - src/gui/dialogs/update_dialog.py
   - src/gui/dialogs/v4_migration_dialog.py
   - automatyczne sprawdzanie i ciche aktualizacje w src/main.py oraz src/gui/main_window.py
   - wbudowany przycisk i kod aktualizacji w src/gui/dialogs/settings_dialog.py
   - setupfiles/update-windows.bat, setupfiles/update-linux.sh, setupfiles/update-mac.sh, setupfiles/legacy/, oraz cały folder updaters/
   - raport/raport.md (zgłoszenie testera po aktualizacji z wersji 3 do 4)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu oraz w .github/workflows/ (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (zabezpieczenie przy wyłączonej samoaktualizacji, brak certyfikatów na starszych maszynach, uprawnienia plików po podmianie, odświeżenie skryptów dla aktualnego DaVinci Resolve 21.1+ po aktualizacji oraz przejście z wersji 3.x do 4.x).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA:
   (A) Co wygląda dziwnie lub podejrzanie (w ilu miejscach dziś siedzą osobne kopie aktualizacji i stare skrypty - i który użytkownik wciąż mógłby przez przypadek w nie trafić)?
   (B) Co obecnie może się psuć u użytkownika (konkretne scenariusze z raportu testera: np. użytkownik klika Aktualizuj na wersji v3 zamiast świeżej instalacji i po restarcie ma mieszankę starych plików z nowymi oraz nieuruchamiającą się aplikację; zamyka okno a aktualizacja w tle przerywa pliki w połowie; albo klika Sprawdź aktualizacje w Ustawieniach i zachowuje się to inaczej niż okienko przy starcie)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji wskaż wprost, jak ma wyglądać aktualizacja dla użytkownika (automatyczna vs ręczna, usuwanie starych folderów aktualizacji, okno powitalne po przejściu z v3).

Po mojej akceptacji i wdrożeniu: napisz testy sprawdzania wersji i aktualizacji (tests/ + run_tests.py), przetestuj na żywo ścieżkę sprawdzania nowej wersji i dialogów aktualizacji/migracji, wygeneruj i obejrzyj zrzuty ekranu okien aktualizacji i migracji v4, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 21 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

### 22. Telemetria, zgłaszanie błędów z logami oraz automatyczne testy i kontrola wydań

- **Co obejmuje:** Okno pytania o zgodę na anonimową telemetrię, wysyłanie jednorazowego sygnału wersji i systemu, zakładka wsparcia i zgłaszania błędów (wysyłanie opisu, zrzutów i paczki logów bez zewnętrznych ciężkich bibliotek), a także główny zestaw testów automatycznych i automatyczne sprawdzanie instalatora w chmurze (GitHub Actions).
- **Dlaczego to ważne:** Dzięki dobremu zbieraniu zgłoszeń od użytkowników i automatycznym testom na wszystkich trzech systemach od razu wyłapiesz problem po każdej zmianie, zanim trafi on do ludzi. Dodatkowo automatyczne testy instalatora i aplikacji są Twoją „polisą ubezpieczeniową” dla wszystkich zacementowanych modułów.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Formularz zgłaszania błędów leży głęboko w pliku okna Ustawień, a zasady działania telemetrii w silniku preferencji. Wydzielenie formularza kontaktu oraz pilnowanie, by automatyczne testy w chmurze obejmowały też najważniejsze testy całej aplikacji (a nie tylko instalator), domknie cały proces cementowania.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 22 planu cementowania: Zgoda na telemetrię, wysyłanie zgłoszeń błędów, główny system testów oraz automatyczne testy na GitHubie.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików - wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i foldery:
   - src/gui/dialogs/telemetry_popup.py
   - wysyłanie telemetrii w src/engine/preferences.py i wywołanie w src/gui/main_window.py
   - zakładka wsparcia i zgłaszania błędów (w tym pakowanie logów i zrzutów ekranu) w src/gui/dialogs/settings_dialog.py
   - run_tests.py i cały folder tests/
   - .github/workflows/build-installer.yml oraz .github/workflows/installer_test.yml
   - przejrzyj przez `gh issue list --state open`, czy zostały jeszcze jakiekolwiek otwarte zgłoszenia wymagające podpięcia do automatyzacji testów lub zamknięcia.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (otwieranie folderu z logami na każdym systemie, działanie bez dodatkowych bibliotek sieciowych i certyfikatów, zgodność komunikatów telemetrii we wszystkich językach bez emoji).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, konkretny raport oparty na REALNYCH PRZYPADKACH Z ŻYCIA UŻYTKOWNIKA I WŁAŚCICIELA PRODUKTU:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia sieciowe, limity wysyłania albo luki w automatach testowych na GitHubie tu występują)?
   (B) Co obecnie może się psuć w praktyce (konkretne scenariusze: np. użytkownik ma problem, otwiera Kontakt, wysyła zgłoszenie i paczka przekracza limit serwera lub zawiera wrażliwe nazwy ścieżek; na Linuksie klika Otwórz folder logów i nic się nie otwiera; albo ktoś wprowadza zmianę w kodzie, testy instalatora przechodzą, a zepsucie aplikacji nie blokuje wydania)?
   (C) Ponumerowana lista pytań decyzyjnych do mnie - przy każdej opcji opisz jasno, co użytkownik widzi przy wysyłaniu zgłoszenia/telemetrii i co blokuje automat na GitHubie.

Po mojej akceptacji i wdrożeniu: uzupełnij testy (tests/ + run_tests.py), przetestuj na żywo pakowanie raportu i jego format wysyłki (oraz otwieranie logów), wygeneruj i obejrzyj zrzuty ekranu okna telemetrii i wsparcia, wpisz pełną dokumentację do docs/CEMENTED.md, zaktualizuj docs/DEV_STATE.md, dopisz krótkie 3-4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit < 4 000 znaków) oraz odhacz Punkt 22 jako [x] ZAKOŃCZONO w ROADMAP_CEMENTING.md.
```

---

## Wskazówka końcowa dotycząca kolejności pracy

- **Kolejność ma znaczenie:** Zacznij od Etapu 1 i 2 (fundamenty startu, pliki danych, silnik audio/AI) oraz Punktu 10A-10C (odchudzenie głównego okna) przed głębokim grzebaniem w ekranach edytora i montażu - dzięki temu kolejne sesje będą znacznie szybsze i bezpieczniejsze.
- **Zasada jednego punktu na sesję:** Nie łącz dwóch punktów w jednej rozmowie. Po skończonej sesji upewnij się, że agent:
  1. przetestował zmienione mechanizmy **na żywo** (nie tylko testy jednostkowe) oraz wygenerował i obejrzał **zrzuty ekranu** zmian widocznych dla użytkownika,
  2. przy zmianach wymagających sprawdzenia na Windowsie 11 lub czystym Linuksie/Waylandzie uruchomił najpierw testy automatyczne w lokalnych maszynach wirtualnych (`badwords-win11`, `badwords-linux-kde`), a dla ręcznego przeklikania / oceny wizualnej / testów z DaVinci Resolve podał krótką instrukcję krok po kroku po polsku,
  3. zaktualizował `docs/CEMENTED.md`, `docs/DEV_STATE.md` oraz dopisał krótkie 3-4 wyrazowe hasło w `.agents/rules/architecture.md` (Sekcja 3, poniżej 4 000 znaków),
  4. **odhaczył zakończony punkt w tym pliku (`ROADMAP_CEMENTING.md`)** (`[x]` na checkliście + `✅ ZAKOŃCZONO` przy nagłówku),
  5. zapisał ewentualne Twoje uwagi lub nowe wymagania z rozmowy do `.agents/rules/lessons_and_standards.md`.
