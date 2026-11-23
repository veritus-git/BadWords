# Plan uporządkowania i zacementowania BadWords (`ROADMAP_CEMENTING.md`)

> **Cel dokumentu:** Uporządkowanie, dopracowanie i zabezpieczenie **obecnie istniejących** funkcji BadWords tak, aby działały niezawodnie na Windowsie, Linuksie i macOS oraz nie psuły się przy kolejnych zmianach.
>
> **Jak z tego korzystać:** Wybierasz jeden punkt na jedną sesję, kopiujesz gotowy **Prompt do wklejenia** do nowej rozmowy z AI i idziesz zrobić herbatę. Agent najpierw tylko analizuje wskazany obszar i przedstawia Ci zwięzły raport z pytaniami decyzyjnymi. Dopiero po Twoich odpowiedziach wdraża zmiany, dopisuje testy ochronne, zapisuje pełny opis w `docs/CEMENTED.md` oraz krótki 3–4 wyrazowy wpis w `.agents/rules/architecture.md` (Sekcja 3).

---

## Przegląd etapów

1. **Etap 1 (v4.1): Fundamenty, start aplikacji i spójność systemowa** — punkty 1–4
2. **Etap 2 (v4.2): Dźwięk, transkrypcja AI i analiza tekstu** — punkty 5–9
3. **Etap 3 (v4.3): Ekran powitalny, edytor, podgląd audio/wideo i okna ustawień** — punkty 10A–10C, 11, 12A–12B, 13–15
4. **Etap 4 (v4.4): DaVinci Resolve, montaż osi czasu, eksport i zapis projektów** — punkty 16–19
5. **Etap 5 (v4.5): Instalator, aktualizacje, zgłaszanie błędów i sprzątanie** — punkty 20–22

---

## Powiązane zgłoszenia z GitHuba (stan bieżący)

- **Otwarte zgłoszenie `#20`** (*lagowanie aplikacji przy filmach trwających ponad 3–5 godzin za każdym razem, gdy słowo jest zaznaczane na czerwono*) → wpięte bezpośrednio do **Punktu 12B** (oraz powiązane z **Punktem 10A** i **14**).
- **Otwarte zgłoszenie `#8`** (*propozycja nowej dużej funkcji: nieliniowe dopasowanie scenariusza i obsługa pracy z AI przy wywiadach*) → uwzględnione jako kontekst przyszłego rozwoju przy porządkowaniu „pod spodem” w **Punkcie 9** (nie wdrażamy tej nowej funkcji podczas cementowania i nie zamykamy zgłoszenia `#8`).
- **Zamknięte zgłoszenia do weryfikacji, czy nic nie wróciło (`#19`, `#18`, `#7`, `#5`, `#3`)** → wplecione w odpowiednie punkty (`1`, `6`, `7`, `16`, `20`), aby upewnić się, że dawne poprawki są kompletne i zabezpieczone testami.

---

## Etap 1 (v4.1): Fundamenty, start aplikacji i spójność systemowa

> Najbardziej kruche elementy, od których zależy to, czy aplikacja w ogóle się uruchomi, nie pomiesza danych roboczych z plikami programu i będzie wyglądać oraz zachowywać się poprawnie na każdym systemie.

---

### 1. Start aplikacji, dobór środowiska Pythona i „samoleczenie” przy uruchomieniu

- **Co obejmuje:** Moment kliknięcia ikony BadWords lub uruchomienia z DaVinci Resolve aż do pokazania ekranu powitalnego. Obejmuje ochronę przed różnymi wersjami Pythona w systemie, ukrywanie migających czarnych okienek na Windowsie, pilnowanie kolejności uruchamiania na starszym Pythonie w Resolve oraz mechanizm automatycznego doinstalowywania brakujących składników przy starcie.
- **Dlaczego to ważne:** To tutaj zdarzają się krytyczne awarie jeszcze zanim zobaczysz okno aplikacji (np. gdy DaVinci Resolve albo systemowy Python próbuje uruchomić BadWords ze swoją niekompatybilną wersją bibliotek albo pojawia się błąd uruchamiania jak w historycznym zgłoszeniu `#18`).
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Mechanizm startowy łączy w jednym miejscu sprawdzanie środowiska, naprawę braków i automatyczną aktualizację przy starcie. Warto wyraźnie rozdzielić sam start okna od napraw i aktualizacji, żeby w przyszłości łatwo dodawać nowe tryby uruchamiania bez ryzyka zawieszenia startu.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 1 planu cementowania: Start aplikacji, środowisko uruchomieniowe i mechanizm samoleczenia przy starcie.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie dogłębną analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i powiązane z nimi elementy:
   - src/main.py
   - raport/message.txt (znany przypadek błędu zgodności wersji Pythona przy starcie z Resolve)
   - sekcja startu i wykrywania środowiska w src/osdoc.py
   - wywołania uruchamiania z zewnętrznych skryptów w setupfiles/windows/, setupfiles/linux/, setupfiles/macos/
   - zgłoszenie GitHub #18 (sprawdź przez `gh issue view 18`, czy problem błędu uruchamiania ze ścieżkami jest w pełni rozwiązany zarówno przy starcie z pulpitu, jak i z Resolve) oraz otwarte zgłoszenia przez `gh issue list --state open`, czy pojawiło się coś nowego w tym obszarze.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź, czy obecne rozwiązanie jest optymalne i spójne między systemami Windows, Linux i macOS (szczególnie uruchamianie jako samodzielna aplikacja vs uruchamianie ze środka DaVinci Resolve oraz ochrona przed cudzym środowiskiem Pythona / Conda).
4. Przygotuj dla mnie po polsku, całkowicie prostym, nietechnicznym językiem (bez nazw funkcji, klas i bez wklejania kodu), zwięzły raport z dokładnie 3 sekcjami:
   (A) Co w tym miejscu wygląda dziwnie lub podejrzanie (jakie są wbudowane obejścia i „łaty” — czy powinny zostać, czy można je bezpiecznie uprościć)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. długie uruchamianie, ciche błędy, konflikty między systemowym Pythonem a wbudowanym środowiskiem, niepotrzebne próby naprawy z internetu)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak dokładnie ma się zachowywać start i awaryjne komunikaty / czego program ma NIE robić bez mojej zgody), żebym mógł krótko odpowiedzieć punkt po punkcie.

Po mojej akceptacji i wdrożeniu zmian pamiętaj o:
- napisaniu testów blokujących regresję (w tests/ i uruchomieniu run_tests.py),
- ewentualnym zamknięciu rozwiązanych powiązanych zgłoszeń na GitHubie przez `gh` (jeśli jakieś otwarte dotyczyły tego punktu),
- wpisaniu pełnej dokumentacji technicznej (działanie, niezmienniki, testy) do docs/CEMENTED.md oraz dopisaniu wyłącznie krótkiego, 3–4 wyrazowego hasła z odesłaniem do docs/CEMENTED.md w .agents/rules/architecture.md (Sekcja 3, z zachowaniem limitu poniżej 4 000 znaków).
```

---

### 2. Rozdzielenie trybu roboczego (DEV) od wersji dla użytkownika oraz porządek w plikach danych

- **Co obejmuje:** Sposób, w jaki BadWords decyduje, gdzie zapisywać ustawienia, pamięć o użytkowniku, zapisy projektów, pliki tymczasowe i dzienniki błędów (logi) — osobno podczas Twojej pracy w repozytorium, a osobno u zwykłego użytkownika po instalacji. Obejmuje też sprzątanie starych plików tymczasowych oraz przenoszenie starych ustawień z poprzednich wersji.
- **Dlaczego to ważne:** Chroni repozytorium przed zaśmiecaniem plikami prywatnymi i gwarantuje, że czyszczenie plików tymczasowych nie skasuje czegoś ważnego w trakcie pracy ani nie zepsuje ścieżek z polskimi znakami czy spacjami na Windowsie.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Główny plik zarządzający ścieżkami systemowymi urósł do ogromnych rozmiarów i zajmuje się jednocześnie ścieżkami dyskowymi, zapisem ustawień, wykrywaniem DaVinci Resolve, sprawdzaniem karty graficznej i przycinaniem okien. Warto wydzielić osobny, czysty obszar tylko dla zarządzania danymi i ścieżkami dyskowymi, żeby nie trzeba było dotykać kodu systemowego przy dodawaniu nowych ustawień.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 2 planu cementowania: Rozdzielenie trybu deweloperskiego od wersji zainstalowanej oraz zarządzanie plikami danych, zapisami i logami.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i foldery:
   - src/osdoc.py (wykrywanie trybu roboczego, foldery ustawień, zapisów, plików tymczasowych, logowanie, migracja starych ustawień, sprzątanie starych plików)
   - src/config/settings_defaults.py
   - src/engine/preferences.py (w części dotyczącej odczytu i zapisu preferencji)
   - raport/logi_macOS_prawdopodobnie_blad_pobierania_ffmpega.log (zwróć uwagę na powielone wpisy w logach)
   - sprawdź przez `gh issue list --state open`, czy któreś otwarte zgłoszenie dotyczy ścieżek danych lub logów.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność zachowania na Windowsie, Linuksie i macOS (uprawnienia do folderów, długie ścieżki i polskie znaki, podwójne zapisywanie wpisów w logu, bezpieczne czyszczenie folderu tymczasowego przy otwartych kilku projektach lub długich sesjach).
4. Przygotuj dla mnie po polsku, całkowicie prostym, nietechnicznym językiem (bez żargonu i bez kodu), zwięzły raport z 3 sekcjami:
   (A) Co w tym miejscu wygląda dziwnie lub podejrzanie (jakie są obecne obejścia, migracje i przestarzałe ścieżki — czy mają zostać)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. utrata ustawień, przepełnianie dysku plikami tymczasowymi, podwójne wpisy w dziennikach błędów, rozjazd między wersją z repozytorium a zainstalowaną)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak dokładnie mają być przechowywane dane, jak długo trzymać pliki tymczasowe, czego ma NIE robić migracja).

Po mojej akceptacji i wdrożeniu pamiętaj o napisaniu testów blokujących regresję (w tests/ i uruchomieniu run_tests.py), wpisaniu pełnej dokumentacji do docs/CEMENTED.md oraz dopisaniu krótkiego 3–4 wyrazowego hasła w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

### 3. Okno bez ramki, własny pasek tytułu, tryb „Zawsze na wierzchu” i płynność animacji między systemami

- **Co obejmuje:** Wygląd i zachowanie głównego okna oraz wyskakujących okienek: przeciąganie za górny pasek, powiększanie na pełny ekran na wybranym monitorze, chowanie białych mignięć przy otwieraniu okien, znikająca ikona aplikacji, przycisk „Zawsze na wierzchu” oraz dopasowanie płynności animacji do odświeżania monitora (60 Hz / 120 Hz / 144 Hz+).
- **Dlaczego to ważne:** Każdy z trzech systemów (Windows 11, macOS, Linux z X11 lub Waylandem) traktuje okna bez systemowej ramki zupełnie inaczej. To jedno z najczęstszych źródeł wizualnych usterek, zacinania przeciągania okna lub błędów przy zmianie monitora.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Część sztuczek do okien i ikon siedzi w głównym oknie i w oknie ustawień zamiast w jednym wspólnym miejscu. Uporządkowanie ich w jednym wspólnym mechanizmie okien sprawi, że każde nowe okienko dodane w przyszłości od razu dostanie dobry wygląd i zachowanie na wszystkich trzech systemach.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 3 planu cementowania: Zachowanie okien bez ramki, paska tytułu, ikony aplikacji, trybu „Zawsze na wierzchu” oraz synchronizacji odświeżania ekranu.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/components/mixins.py
   - src/gui/components/titlebar.py
   - src/gui/utils.py
   - src/gui/vsync.py
   - metody okna i odświeżania w src/osdoc.py (wymuszanie ciemnego paska, zawsze na wierzchu)
   - fragmenty dotyczące odświeżania ikony, pełnego ekranu i „Zawsze na wierzchu” w src/gui/main_window.py oraz src/gui/dialogs/settings_dialog.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux (X11 i Wayland, KDE/GNOME) oraz macOS (ikona w Docku, skróty okna, brak białego błysku przy otwieraniu, zachowanie na wielu monitorach o różnym skalowaniu i odświeżaniu).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie systemowe obejścia i niskopoziomowe sztuczki są tu użyte — które są niezbędne na danym systemie, a które wyglądają ryzykownie)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. zrywanie przeciągania okna, obcięte krawędzie, znikająca ikona, migotanie lub brak działania „Zawsze na wierzchu”)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma zachowywać się okno przy maksymalizacji, na drugim monitorze, na macOS i Linuksie).

Po mojej akceptacji i wdrożeniu napisz testy (dla zmian widocznych na ekranie wygeneruj zrzuty ekranu i sam je obejrzyj), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

### 4. Spójność języków, brak emoji i tekstów na sztywno, wygląd paska postępu i skalowanie interfejsu

- **Co obejmuje:** Zgodność wszystkich 11 wersji językowych, usuwanie tekstów wpisanych „na sztywno” (np. po polsku mimo wybranego angielskiego), całkowite wyeliminowanie systemowych emotek z interfejsu na rzecz czystych ikon wektorowych, ochronę przed narzucaniem systemowych kolorów (np. czarny tekst na czarnym tle) oraz poprawne skalowanie (75%–150%) i zaokrąglenia pasków postępu.
- **Dlaczego to ważne:** Testerzy zgłaszali dokładnie te problemy w raportach: polskie dymki podpowiedzi przy włączonym angielskim języku, czarny tekst na ciemnym tle, kwadratowo przycięte rogi paska postępu oraz ostrzeżenia o nieobsługiwanym stylu czcionki w dolnym odtwarzaczu.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Pomocniczy przycisk informacji „(i)” oraz rysowanie ikon wektorowych są powielone w kilku plikach zamiast być w jednym miejscu, a część okienek ma własne słowniczki zamiast korzystać z centralnych tłumaczeń. Scalenie tego bardzo ułatwi dodawanie kolejnych ekranów i języków.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 4 planu cementowania: Spójność tłumaczeń, usunięcie tekstów i emoji wpisanych na sztywno, odporność kolorów motywu na systemowe style, paski postępu oraz skalowanie ekranu.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te obszary:
   - src/i18n/ (mechanizm ładowania i wszystkie pliki językowe)
   - src/config/app_constants.py, src/config/palette.py, src/config/languages.py
   - src/gui/widgets/progress_bar.py i użycie pasków postępu w src/gui/views/processing_view.py oraz src/gui/dialogs/splash_screen.py
   - miejsca z potencjalnym tekstem lub emoji na sztywno w src/gui/dialogs/ (m.in. export_dialog.py, v4_migration_dialog.py, settings_dialog.py), src/gui/main_window.py, src/gui/components/audio_preview.py, src/gui/components/video_preview.py
   - raport/raport.md (zgłoszenia testerów o czarnym tekście na czarnym tle, języku podpowiedzi i przyciętych rogach paska postępu)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux (zwłaszcza KDE/GTK narzucające własną paletę) i macOS przy różnych poziomach powiększenia interfejsu (75%–150%).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (gdzie ominięto główny system tłumaczeń, gdzie zostały doraźne łaty lub duplikaty ikon)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (mieszanie języków, nieczytelne napisy na jasnych motywach systemu, obcięte zaokrąglenia, emoji w komunikatach)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jakie zachowanie jest docelowe przy braku tłumaczenia, zamianie emotek na ikony i skalowaniu ekranu).

Po mojej akceptacji i wdrożeniu napisz/rozszerz testy wizualne i regresyjne (w tests/ i uruchom run_tests.py), wygeneruj zrzuty ekranu zmienionych elementów do sprawdzenia, wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

## Etap 2 (v4.2): Dźwięk, transkrypcja AI i analiza tekstu

> Serce sztucznej inteligencji i obliczeń w BadWords: przygotowanie dźwięku, bezpieczne wykorzystanie karty graficznej lub procesora, rozpoznawanie mowy oraz porównywanie ze scenariuszem i wykrywanie powtórek.

---

### 5. Wyciąganie dźwięku z wideo/osi, normalizacja głośności i wstępne wykrywanie ciszy

- **Co obejmuje:** Wyszukiwanie narzędzia FFmpeg na komputerze użytkownika, wyciąganie ścieżki dźwiękowej z plików wideo lub audio, wyrównywanie głośności przed analizą, wykrywanie fragmentów ciszy oraz łączenie krótkich wypowiedzi w dłuższe paczki („wyspy dźwięku”) dla AI.
- **Dlaczego to ważne:** Z logów wynikał problem z brakiem wykrywania FFmpeg na macOS. Dodatkowo od jakości wyciągniętego dźwięku i łączenia pauz zależy dokładność zarówno cięcia ciszy, jak i całej transkrypcji — przy długich lub wielokanałowych plikach drobny błąd powoduje przesunięcia w czasie lub brak dźwięku.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Logika wyciągania dźwięku jest podzielona między dwa pliki silnika (jeden robi podstawową obróbkę i normalizację, drugi składa wiele plików i bada ich parametry). Zebranie reguł pracy z mediami i FFmpeg w jedno czytelne miejsce ułatwi w przyszłości obsługę np. wielu ścieżek lektorów naraz.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 5 planu cementowania: Wyszukiwanie FFmpeg, wyciąganie dźwięku z klipów, normalizacja głośności, wykrywanie ciszy i grupowanie fragmentów mowy.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i powiązania:
   - src/engine/audio_extraction.py
   - część przygotowania mediów i łączenia dźwięku w src/engine/audio_engine.py
   - wyszukiwanie narzędzia FFmpeg w src/osdoc.py
   - raport/logi_macOS_prawdopodobnie_blad_pobierania_ffmpega.log
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź, czy rozwiązanie jest optymalne i spójne między Windows, Linux i macOS (różne formaty wideo/audio, ścieżki ze spacjami lub polskimi znakami, bardzo długie nagrania, pliki bez dźwięku albo z kilkoma ścieżkami audio).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie są obejścia przy wykrywaniu ciszy, normalizacji i szukaniu FFmpeg — czy powinny zostać)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. błąd braku FFmpeg, zbyt długie mielenie przy dużych plikach, zrywanie przy nietypowych kodekach lub pustych ścieżkach)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma reagować program przy braku dźwięku, nietypowych ścieżkach i braku FFmpeg).

Po mojej akceptacji i wdrożeniu napisz testy blokujące regresję (w tests/ i uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

### 6. Wykrywanie karty graficznej (NVIDIA / Apple Silicon / procesor) i bezpieczny powrót na procesor

- **Co obejmuje:** Automatyczne sprawdzanie przed startem transkrypcji, czy komputer ma sprawną kartę graficzną NVIDIA (z wymaganą wersją sterowników i bibliotekami na dysku), czy działa na procesorze Apple Silicon (M1–M5), czy powinien spokojnie przełączyć się na zwykły procesor — bez nagłego zamykania programu.
- **Dlaczego to ważne:** Na słabszych lub szkolnych komputerach, przy niekompletnych sterownikach NVIDIA albo braku części bibliotek graficznych (jak w zgłoszeniu GitHub `#19`), silnik AI potrafił nagle wybuchnąć podczas uruchamiania. Choć wprowadzono już poprawki awaryjne, ten obszar wymaga pełnego sprawdzenia na wszystkich trzech systemach.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Część wykrywania sprzętu leży w module systemowym, a druga w module transkrypcji, przy czym test karty uruchamiany jest przez sklejany dynamicznie tekst skryptu. Uporządkowanie wykrywania sprzętu w jednym miejscu bez sklejanych skryptów bardzo ułatwi dodanie w przyszłości nowych akceleratorów.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 6 planu cementowania: Wykrywanie i weryfikacja sprzętu dla AI (NVIDIA, Apple Silicon, CPU) oraz bezpieczne przełączanie awaryjne na procesor.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te obszary:
   - sprawdzanie karty graficznej, sterowników, bibliotek i doboru wątków procesora w src/osdoc.py
   - sprawdzanie sprawności karty, wybór trybu obliczeń i obsługę Apple Silicon w src/engine/transcription.py
   - testy w tests/test_host_env_fixes.py (żeby zrozumieć, co już jest zabezpieczone)
   - zamknięte zgłoszenie GitHub #19 (`gh issue view 19`) i sprawdź otwarte zgłoszenia (`gh issue list --state open`), czy coś nowego dotyczy CUDA/GPU.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność i bezpieczeństwo na Windowsie, Linuksie i macOS (tryb Auto, ręcznie wymuszone GPU bez karty lub ze starym sterownikiem, komputer z małą ilością pamięci RAM, różnice między Intel Mac a Apple Silicon).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie są teraz obejścia dla sterowników, bibliotek graficznych i pamięci — które chronią przed awarią i muszą zostać)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. długie opóźnienie przed transkrypcją na testowanie sprzętu, mylące komunikaty dla użytkownika, błędny wybór precyzji)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (kiedy program ma informować o przejściu na wolniejszy procesor, a kiedy robić to po cichu).

Po mojej akceptacji i wdrożeniu napisz/rozbuduj testy w tests/ (uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/engine/transcription.py
   - src/config/analysis_params.py (domyślne podpowiedzi i ustawienia AI)
   - src/handlers/analysis_worker.py
   - wywołania analizy i strumieniowania w src/engine/audio_engine.py oraz odbiór fragmentów na żywo w src/gui/main_window.py i src/gui/components/transcription_canvas.py
   - historyczne zgłoszenia GitHub #7, #3 i #19 (`gh issue view 7`, `gh issue view 3`) — sprawdź szczególnie, czy propozycja czytelnego komunikatu przy zablokowanym internecie/pobieraniu modelu ze zgłoszenia #7 została w pełni i wielojęzycznie wdrożona.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź działanie i spójność na Windows, Linux i macOS (pobieranie przy słabym internecie lub przerwaniu w połowie, ścieżki z polskimi znakami, równoległe przetwarzanie kawałków, zachowanie przycisku zatrzymania analizy, czyszczenie plików tymczasowych).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (sklejane w locie skrypty, udawanie konsoli przy pobieraniu, poprawki zgodności — co musi zostać, a co jest bardzo kruche)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. zacięty pasek pobierania, niejasny komunikat przy braku sieci lub miejsca na dysku, różnice w języku komunikatów podczas pobierania modelu)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma działać przerwanie pobierania/analizy, komunikaty o braku pamięci lub sieci).

Po mojej akceptacji i wdrożeniu napisz testy blokujące regresję (w tests/ i uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i testy:
   - src/algorithms.py (czyszczenie halucynacji, samodzielna analiza powtórek, wchłanianie niezrozumiałych fragmentów, reguła pierwszeństwa oznaczeń ręcznych, rozchodzenie się zmian)
   - metody budowania struktury słów i analizy w src/engine/audio_engine.py
   - testy w tests/test_algorithms.py i tests/test_data_contracts.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź poprawność działania na skrajnych przypadkach (puste nagrania, brak wykrytej mowy, bardzo długie powtórzenia, przełączanie filtrów po ręcznej edycji, nieangielskie znaki i interpunkcja).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie specjalne wyjątki i nieoczywiste powiązania przy pierwszym słowie listy albo między warstwami kolorów tu występują)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. niechciane skasowanie ręcznej decyzji po włączeniu wypełniaczy, gubienie fragmentów `(...)`, dziwne cięcie zdań)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak dokładnie mają się zachowywać ręczne poprawki wobec automatycznych przełączników).

Po mojej akceptacji i wdrożeniu rozbuduj testy w tests/ (uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

### 9. Wczytywanie scenariuszy (DOCX/PDF/TXT), porównanie ze scenariuszem i widok obok siebie (Side-by-Side)

- **Co obejmuje:** Wczytywanie scenariuszy z dysku lub wklejanie tekstu w panelu bocznym, wyciąganie specjalistycznych słów-kluczy ze scenariusza jako podpowiedzi dla AI, silnik porównujący nagrane słowa ze scenariuszem oraz okno/widok porównania linijka po linijce (Side-by-Side) ze skokiem do odpowiedniego miejsca na osi.
- **Dlaczego to ważne:** Porównywanie ze scenariuszem to jeden z największych wyróżników BadWords. W praktyce duże scenariusze lub nietypowo sformatowane pliki PDF/DOCX potrafią gubić polskie znaki, mylić dopasowanie przy długich dygresjach lub rozsynchronizować widok Side-by-Side względem głównego tekstu.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak — bardzo ważne dla przyszłości.** Silnik porównywania i budowanie widoku Side-by-Side są bardzo długie i ściśle powiązane z uruchamianiem skryptu pomocniczego z wnętrza silnika audio. Warto je wydzielić w czytelny sposób z myślą o otwartym zgłoszeniu **GitHub `#8`** (przyszła rozbudowa o nieliniowe dopasowanie scenariusza i pracę z wywiadami), ale **w tym etapie nie wdrażamy nowych funkcji z `#8`** — jedynie porządkujemy obecne porównywanie liniowe tak, by w przyszłości dało się łatwo dołożyć nowe tryby.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 9 planu cementowania: Obsługa plików scenariusza (DOCX/PDF/TXT), podpowiedzi trudnych słów dla AI, algorytm porównania ze scenariuszem oraz widok porównania obok siebie (Side-by-Side).

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te obszary:
   - wczytywanie DOCX/PDF, dopasowywanie ze scenariuszem i budowanie układu Side-by-Side w src/algorithms.py
   - wyciąganie trudnych słów i uruchamianie porównania w src/engine/audio_engine.py
   - src/gui/panels/script_panel.py
   - obsługa wczytywania skryptu, uruchamiania analizy porównawczej i widoku Side-by-Side w src/gui/main_window.py
   - zobacz też otwarte zgłoszenie GitHub #8 (`gh issue view 8`) wyłącznie jako kontekst przyszłego kierunku rozwoju — NIE wdrażaj teraz funkcji z #8 i NIE zamykaj #8; sprawdź tylko, czy obecne porządki ułatwią jego realizację w przyszłości.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź zachowanie na Windows, Linux i macOS (kodowanie polskich i międzynarodowych znaków w plikach TXT/PDF/DOCX, bardzo duże dokumenty, sytuacja gdy lektor przeczytał fragment w innej kolejności albo zaimprowizował długi blok).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie skróty lub osobne sposoby uruchamiania tu siedzą i czy są potrzebne)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. zacięcia przy dużych PDF-ach, rozjazd zaznaczenia w widoku obok siebie, błędne oznaczanie brakujących zdań)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak program ma traktować uszkodzone PDF-y, wielkie scenariusze, brakujące akapity i synchronizację po kliknięciu słowa).

Po mojej akceptacji i wdrożeniu napisz testy regresyjne (w tests/ i uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie tylko ten fragment projektu:
   - metody statystyk, legendy kolorów, podglądu cięć, wycinania koloru i eksportu/kopiowania tekstu w src/gui/main_window.py
   - src/gui/panels/colors_panel.py oraz src/gui/panels/assembly_panel.py
   - otwarte zgłoszenie GitHub #20 (`gh issue view 20`) — sprawdź, czy przeliczanie statystyk i legendy przy każdym kliknięciu słowa dokłada się do lagów na nagraniach 3–5+ godzinnych.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej elementami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź, gdzie statystyki i legenda są wywoływane z zewnątrz (np. panel ciszy, płótno transkrypcji, cofanie zmian, montaż) i jak zachowują się na długich projektach.
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obliczenia siedzą w głównym oknie mimo że powinny działać osobno, i czy przy każdym zaznaczeniu słowa przelicza się cały dokument)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. opóźnienia po kliknięciu, niespójne liczniki między panelem ciszy a legendą kolorów)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak dokładnie ma wyglądać wydzielenie tego obszaru i czy przy okazji poprawić drobne niespójności w licznikach lub eksporcie tekstu).

Po mojej akceptacji i wdrożeniu napisz testy dla liczników, legendy i eksportu tekstu (w tests/ i uruchom run_tests.py oraz kontrolę GUI), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

### 10B. Odchudzenie głównego okna (część 2): paski boczne, skróty klawiszowe, obsługa zdarzeń i przyciski markerów

- **Co obejmuje:** Wydzielenie z głównego okna drugiego niezależnego bloku: zarządzania paskami bocznymi i zapamiętywania ich układu, przełączania ekranów (Powitanie / Przetwarzanie / Edytor), budowania przycisków wyboru kolorów markerów, zarządzania skrótami klawiszowymi (w tym blokowania skrótów podczas pisania w polach tekstowych) oraz trybu „Zawsze na wierzchu” / maksymalizacji.
- **Dlaczego to ważne:** Obsługa skrótów i pasków bocznych jest bardzo wrażliwa na kolejność kliknięć i różnice między Windows, Linux i macOS (np. kiedy piszesz nazwę pliku albo szukasz w tekście i naciśniesz klawisz koloru). Osobny, uporządkowany moduł od skrótów i układu okien da pewność, że nowe przyciski lub skróty nie zepsują pisania w polach tekstowych.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Drugi krok odchudzania głównego okna — pozwoli w przyszłości bez stresu dodawać nowe zakładki na pasku bocznym i nowe skróty.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 10B planu cementowania: Wydzielenie z głównego okna zarządzania paskami bocznymi, przełączania ekranów, przycisków markerów i skrótów klawiszowych.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie tylko ten fragment projektu:
   - metody pasków bocznych, przełączania aktywności, przycisków markerów, skrótów klawiszowych, filtrowania zdarzeń oraz przełączania stron w src/gui/main_window.py
   - src/gui/panels/main_workspace_panel.py, src/gui/views/editor_view.py, src/gui/views/processing_view.py
   - src/gui/dialogs/overlay.py (styk z globalnym przechwytywaniem kliknięć i klawisza Enter)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej elementami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność na Windows, Linux i macOS (skróty klawiszowe podczas pisania w wyszukiwarce lub polu scenariusza, zapamiętywanie układu pasków bocznych, kolejność rysowania przejść między ekranami).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie ręczne obejścia dla skrótów, fokusu lub przycisków markerów siedzą obecnie w głównym oknie)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. uruchamianie skrótu koloru podczas wpisywania tekstu, gubienie zapisanego układu paneli bocznych)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma zachowywać się przełączanie pasków bocznych i skróty w oknach pomocniczych).

Po mojej akceptacji i wdrożeniu napisz testy (w tests/ i uruchom run_tests.py oraz kontrolę GUI), zrób zrzut ekranu układu edytora z paskami do weryfikacji, wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie tylko ten fragment projektu:
   - metody uruchamiania i zakończenia analizy, Szybkiej Ciszy, proxy w tle, wczytywania projektu w tle, komunikatów statusu, sprawdzania aktualizacji/telemetrii oraz zamykania w src/gui/main_window.py
   - src/handlers/analysis_worker.py
   - src/gui/components/top_status_island.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej elementami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (co się dzieje, gdy użytkownik zamknie okno podczas trwającej transkrypcji lub budowania podglądu wideo, czy blokada edytora podczas strumieniowania na żywo zawsze zdejmuje się po błędzie).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie są obejścia przy wczytywaniu w tle, blokowaniu okna na czas analizy lub sprawdzaniu aktualizacji na starcie)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. zostające w tle procesy po zamknięciu okna, zablokowany interfejs po nieudanej analizie, nakładające się komunikaty statusu)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma zachowywać się zamykanie podczas pracy w tle i kolejność okienek powitalnych/aktualizacji po uruchomieniu).

Po mojej akceptacji i wdrożeniu napisz testy (w tests/ i uruchom run_tests.py oraz kontrolę GUI), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/views/welcome_view.py
   - src/gui/widgets/file_drop_zone.py
   - src/gui/components/track_options_drawer.py
   - obsługa ekranu powitalnego, wyboru osi/ścieżek i Szybkiej Ciszy w src/gui/main_window.py i src/engine/audio_engine.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (przeciąganie plików z eksploratora/Findera/menedżera plików, uruchamianie ze środka DaVinci Resolve vs samodzielne, zachowanie gdy DaVinci Resolve nie jest zainstalowane, płynność animacji zwijania i rozwijania).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (obejścia w animacjach, wykrywaniu otwartego Resolve czy odświeżaniu listy ścieżek)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. wrzucenie nieobsługiwanego pliku, utrata zaznaczenia ścieżek po przełączeniu osi czasu, zacinające się animacje lub ucięte napisy)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma reagować lista na duplikaty plików, brak Resolve, mieszane rozdzielczości w kolejce i tryb Szybka Cisza).

Po mojej akceptacji i wdrożeniu napisz testy (w tests/ i uruchom run_tests.py), wygeneruj zrzuty ekranu obu trybów ekranu powitalnego i sam je sprawdź, wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/components/transcription_canvas.py
   - src/gui/components/search_overlay.py
   - src/handlers/undo_manager.py
   - src/gui/dialogs/marker_dialog.py
   - src/gui/dialogs/overlay.py (globalny filtr kliknięć i opóźnienie dymków)
   - połączenie edytora z legendą i skrótami w src/gui/main_window.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność na Windows, Linux i macOS (różnice w skrótach Ctrl vs Cmd na Macu, szybkie przewijanie kółkiem myszy i gładzikiem, klikanie podczas strumieniowania słów na żywo, intuicyjność przełączania trybów myszy).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (obejścia w układaniu tekstu, obsłudze kliknięć poza polami lub w rysowaniu przekreśleń)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. Cofnij/Ponów nieodświeżające statystyk lub podglądu audio, problemy z wyszukiwarką lub własnymi markerami)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak dokładnie ma działać zaznaczanie ramką vs tekstem, jak mają wyglądać przekreślenia przy nakładających się kolorach, co ma obejmować Cofnij/Ponów).

Po mojej akceptacji i wdrożeniu napisz testy regresyjne (w tests/ i uruchom run_tests.py), wygeneruj zrzuty ekranu edytora do weryfikacji, wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

### 12B. Wydajność edycji i przeliczania cięć na wielogodzinnych nagraniach (zgłoszenie GitHub `#20`)

- **Co obejmuje:** Kompleksowe zbadanie i wyeliminowanie zacinania programu podczas zaznaczania słów (szczególnie na czerwono) przy bardzo długich filmach i podcastach trwających 3–5 godzin i więcej — zgodnie z otwartym zgłoszeniem na GitHubie (`#20`), gdzie przy 1 godzinie wszystko działa płynnie, a powyżej 3 godzin każde zaznaczenie słowa powoduje wyraźne przycięcie.
- **Dlaczego to ważne:** Przy kilkugodzinnym materiale transkrypcja ma dziesiątki tysięcy słów. Jeśli po zaznaczeniu choćby jednego słowa program za każdym razem od nowa układa cały dokument, przerysowuje całą falę dźwiękową, przelicza całą oś czasu i planuje zapis na dysk — interfejs zaczyna stawać na ułamek sekundy lub dłużej przy każdym ruchu myszą.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Wymaga wyraźnego oddzielenia lekkiego odświeżenia samego widocznego fragmentu ekranu od ciężkiego pełnego przeliczania całego projektu, aby przyszłe funkcje edytora także działały błyskawicznie nawet przy 8-godzinnych transmisjach.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 12B planu cementowania: Wydajność zaznaczania i malowania słów oraz przeliczania podglądu cięć przy wielogodzinnych nagraniach (otwarte zgłoszenie GitHub #20).

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Najpierw przeczytaj dokładnie zgłoszenie GitHub #20 (`gh issue view 20`), a potem prześledź cały łańcuch zdarzeń od kliknięcia / pomalowania słowa na czerwono aż po koniec odświeżenia ekranu w tych plikach:
   - src/gui/components/transcription_canvas.py (przeliczanie układu i odświeżanie po zmianie koloru słowa)
   - wywołania odświeżania podglądu cięć, statystyk i legendy kolorów w src/gui/main_window.py (lub wydzielonym module z Punktu 10A)
   - src/engine/audio_engine.py (przeliczanie cięć osi czasu wywoływane w trakcie edycji)
   - src/gui/components/waveform_timeline.py oraz src/gui/components/audio_preview.py (reakcja wykresu fali i odtwarzacza na zmianę koloru słowa)
   - src/handlers/autosave_manager.py (czy przy każdym słowie nie kopiuje się w pamięci dziesiątek tysięcy słów)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku w tym łańcuchu reakcji (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź zachowanie i zmierz lub oszacuj czas reakcji dla nagrania 1-godzinnego vs 5-godzinnego (dziesiątki tysięcy słów) na Windows, Linux i macOS.
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co w tym łańcuchu odświeżania wygląda dziwnie lub nadmiarowo (co ciężkiego wykonuje się niepotrzebnie przy zaznaczeniu pojedynczego słowa)?
   (B) Co dokładnie powoduje zacinanie z punktu widzenia użytkownika w zgłoszeniu #20 i czy są jeszcze inne ukryte wąskie gardła przy 5-godzinnych plikach?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (np. czy przy szybkim malowaniu wystarczy odświeżyć statystyki i falę z minimalnym opóźnieniem po puszczeniu myszy, jakie opóźnienie jest dla mnie akceptowalne).

Po mojej akceptacji i wdrożeniu:
- napisz test wydajnościowy / regresyjny na dużym zestawie słów (odpowiadającym 5 godzinom mowy) w tests/ i uruchom run_tests.py,
- sprawdź czy wygląd na ekranie (przekreślenia, legenda, wykres fali) nadal odświeża się bezbłędnie (wygeneruj zrzuty ekranu),
- zamknij zgłoszenie #20 na GitHubie przez `gh issue close 20` z krótkim podaniem przyczyny i naprawy,
- wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

### 13. Dolny odtwarzacz audio/wideo, omijanie cięć w czasie rzeczywistym i regulacja głośności

- **Co obejmuje:** Dolny dok odtwarzania: przyciski Play/Stop/Przewijanie, suwak czasu, szybkość odtwarzania, zwijanie i rozwijanie panelu, dynamiczne omijanie wyciętych słów i ciszy w locie („Skip Cuts”), głośność oraz automatyczne pobieranie brakującego dźwięku z Resolve po wczytaniu starego projektu.
- **Dlaczego to ważne:** Testerzy zgłaszali kłopoty z niedziałającymi przyciskami odtwarzacza oraz ostrzeżenia o stylach czcionek w tym panelu. Dodatkowo odtwarzacz zawiera osobne obejście do sterowania głośnością na Linuksie (poprzez systemowy mikser dźwięku) oraz sztuczkę wyciszania przy przeskoku, żeby uniknąć trzasków w słuchawkach — wszystko to musi działać gładko na każdym systemie.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Odtwarzacz łączy w sobie sterowanie oknem, logikę przeskakiwania wycięć, podgląd wideo i dogrywanie brakującego dźwięku w jednym rozbudowanym pliku. Wydzielenie logiki omijania cięć i synchronizacji ze słowami do osobnej małej części zapobiegnie błędom rozsynchronizowania przy przyszłych zmianach odtwarzacza.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 13 planu cementowania: Dolny odtwarzacz audio/wideo, automatyczne omijanie wyciętych fragmentów na żywo, głośność między systemami oraz dogrywanie brakującego audio.

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/components/audio_preview.py
   - src/gui/components/video_preview.py
   - src/gui/widgets/sliders.py
   - przygotowanie pliku audio do podglądu w src/engine/audio_extraction.py
   - powiązania odtwarzacza z edytorem i oknem głównym w src/gui/main_window.py
   - raport/raport.md (zgłoszenie testera o problemach z odtwarzaczem)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (różne silniki multimedialne wbudowane w system, działanie regulacji głośności i suwaka na Linuksie bez narzędzi systemowego miksera, płynność przeskoku nad wieloma krótkimi wycięciami pod rząd bez trzasków ani zawieszeń, synchronizacja napisu czasu i podświetlanego słowa w tekście).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie systemowe obejścia głośności, zapobiegania trzaskom i uruchamiania odtwarzania są tu zastosowane)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. niedziałające przyciski w określonym stanie, utrata synchronizacji podświetlenia słów przy prędkości 1.5x/2x, zacinanie przy serii gęstych cięć, ostrzeżenia stylu w logu)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak dokładnie ma zachowywać się przycisk Play po końcu nagrania, po kliknięciu wyciętego słowa i przy braku wygenerowanego dźwięku podglądu).

Po mojej akceptacji i wdrożeniu napisz testy dla wyliczania przedziałów do pominięcia i czasu odtwarzania (w tests/ i uruchom run_tests.py), zweryfikuj wygląd na zrzutach ekranu, wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/engine/waveform.py
   - src/gui/components/waveform_timeline.py
   - src/gui/panels/silence_panel.py
   - generowanie podglądu wideo 360p i dostrajanie przedziałów ciszy w src/engine/audio_engine.py oraz src/handlers/analysis_worker.py
   - uruchamianie przeliczania ciszy i proxy w tle w src/gui/main_window.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność na Windows, Linux i macOS (sprzętowe vs programowe tworzenie wideo 360p, zachowanie przy wielokrotnym zmienianiu suwaków bez zacinania, synchronizacja przybliżenia fali z podglądem cięć i wieloma klipami w kolejce).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia przy wykrywaniu sprzętu wideo, buforowaniu wykresu lub wygaszaniu statystyk są w środku)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. błąd przy tworzeniu wideo podglądu na starszych kartach, rozjazd fali dźwiękowej i wskaźnika pozycji przy zoomie, nieoczekiwane zużycie pamięci przy długich podcastach)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma działać generowanie proxy dla wielu plików o różnych proporcjach, jak zachować przybliżenie fali po przeliczeniu ciszy).

Po mojej akceptacji i wdrożeniu napisz testy regresyjne (w tests/ i uruchom run_tests.py), zrób zrzuty ekranu wykresu fali oraz panelu ciszy do sprawdzenia, wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

### 15. Okno Ustawień i biblioteka własnych kontrolek interfejsu

- **Co obejmuje:** Okno Ustawień (wyszukiwarka opcji, tryb Podstawowy vs Zaawansowany, płynne przyciemnianie opcji XML/DRT, zakładki, eksport/import ustawień, przywracanie domyślnych) oraz biblioteka własnych kontrolek (przełączniki, listy rozwijane z przewijanym długim tekstem, przyciski nagrywania skrótów myszy i klawiatury, przycisk dzielony Assemble).
- **Dlaczego to ważne:** Okno Ustawień ma ponad 3,3 tys. linijek, a zbiór własnych przycisków ponad 2,7 tys. linijek — i niemal każdy ekran aplikacji z nich korzysta! Jedna zmiana w liście rozwijanej czy przycisku potrafi popsuć wygląd wielu okien naraz, a w samych ustawieniach siedzą wbudowane kopie logiki aktualizacji i zgłaszania błędów.
- **Porządki „pod spodem” pod przyszłe funkcje:** **Tak.** Zarówno okno Ustawień, jak i plik z przyciskami przydałoby się rozbić na mniejsze, tematyczne części, zachowując pełną wsteczną zgodność, aby łatwo dodawać nowe ustawienia w przyszłości.

**Prompt do wklejenia:**
```text
Przeanalizuj punkt 15 planu cementowania: Okno Ustawień oraz wspólne własne kontrolki interfejsu (przyciski, przełączniki, listy rozwijane, przechwytywanie skrótów).

ZASADY PRACY:
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/dialogs/settings_dialog.py
   - src/gui/widgets/buttons.py
   - src/gui/widgets/delegates.py
   - src/gui/widgets/labels.py
   - src/gui/widgets/language_selector.py
   - src/gui/widgets/layouts.py i splitters.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność na Windows, Linux i macOS (zwłaszcza działanie list rozwijanych w oknach bez ramki, skalowanie 75%–150%, wyszukiwarka ustawień, rozpoznawanie trybów myszki niezależnie od języka interfejsu, skróty z klawiszem Cmd na macOS).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie są obejścia np. z przełączaniem języka w locie, odświeżaniem ikony, wbudowanym własnym updaterem lub sprawdzaniem trybu myszki po tekście)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. znikające lub zasłonięte menu rozwijane na Linuksie/macOS, źle zapamiętane ustawienie po anulowaniu, niedziałający skrót po zmianie)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma działać zapis vs Anuluj, wyszukiwanie opcji podstawowych i zaawansowanych oraz dzielenie pliku kontrolek).

Po mojej akceptacji i wdrożeniu sprawdź/rozszerz testy w tests/test_settings_and_version.py (uruchom run_tests.py), wygeneruj i obejrzyj zrzuty ekranu zakładek Ustawień, wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/api/resolve_handler.py
   - src/api/resolve_bridge.py
   - setupfiles/BadWords Bridge.lua
   - wykrywanie i wdrażanie skryptów Resolve w src/osdoc.py oraz sprawdzenie wywołań w installer/src/engine.rs
   - testy odizolowania od Resolve w tests/test_host_env_fixes.py
   - historyczne zgłoszenie GitHub #5 (`gh issue view 5`) oraz sprawdź otwarte zgłoszenia (`gh issue list --state open`), czy pojawiły się nowe problemy z łącznością Resolve.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów; sprawdź też, czy w src/bridge/ nie zostały jakieś puste/stare ślady).
3. Sprawdź spójność między Windows, Linux i macOS (w tym wersja Mac App Store w piaskownicy systemowej, kodowanie polskich znaków między Lua a Pythonem w skrzynce plików, blokowanie dostępu do pliku w tym samym ułamku sekundy na Windowsie).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia dla darmowego Resolve 21.1+, odczytu zablokowanych plików na Windowsie lub wersji z Mac App Store są tu zastosowane)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. zawieszenie podczas skoku na osi, błędne rozpoznanie edycji Free vs Studio, rozłączenie mostka w połowie długiego renderowania)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma się zachowywać program przy utracie połączenia z Resolve w trakcie pracy, czy i kiedy przypominać o uruchomieniu mostka).

Po mojej akceptacji i wdrożeniu dopisz testy symulujące brak Resolve i komunikację mostka (w tests/ i uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i testy:
   - src/assembler.py (część DRT, czyszczenie Media Pool, dokładne wyliczanie klatkaży i metadanych startowych)
   - obliczanie operacji cięć i uruchamianie montażu w src/engine/audio_engine.py
   - budowanie i importowanie osi czasu przez XML w src/api/resolve_handler.py
   - src/gui/panels/assembly_panel.py oraz panel legendy i montażu w src/gui/main_window.py
   - testy w tests/test_timeline_cuts.py i tests/test_assembler_xml.py
   - raport/raport.md (uwaga o rozjechanych cięciach na osi subframowej)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS oraz dla skrajnych osi czasu (ułamkowe klatkaże, różne przesunięcia początkowego kodu czasowego np. 01:00:00:00, wiele ścieżek audio i wideo, klipy złożone / napisy / przejścia, napisy w językach narodowych w nazwach klipów).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie obejścia przy poprawianiu plików DRT, ukrywaniu ekranu w Resolve podczas importu lub obsłudze Media Pool są obecnie używane)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. rozjazd przy podklatkach, problem z odlinkowanymi ścieżkami, duble plików w Media Pool lub zablokowane opcje między XML a DRT)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma działać montaż na pustych lukach, jak zachowywać nieoznaczone ścieżki tła / muzyki i co robić przy złożonych klipach).

Po mojej akceptacji i wdrożeniu rozbuduj testy dokładności klatkowej i wygenerowanych osi czasu (w tests/ i uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/gui/dialogs/export_dialog.py
   - generatory formatów FCP7 XML, OTIO, FCPXML, EDL oraz bezpośrednie cięcie bezstratne/FFmpeg w src/assembler.py
   - przygotowanie przepisu cięcia i wykonanie w src/engine/audio_engine.py
   - wywołanie okna eksportu i montażu w trybie plikowym w src/gui/main_window.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (zapisywanie ścieżek do plików ze spacjami, polskimi znakami i literami dysków Windowsa jako poprawnych adresów dla Premiere/FCP/Resolve, wieloklipowa kolejka plików o różnych parametrach, przypadek gdy brakuje biblioteki OTIO).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie są skróty, powielone fragmenty lub obejścia w formacie ścieżek, emotka zapasowa w oknie eksportu czy bezstratnym cięciu)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. błąd przy mieszanych klatkażach w kolejce, nieotwierający się plik w Premiere/Final Cut, źle dobrane ścieżki audio w EDL/FCPXML)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma działać mieszana kolejka plików o różnej rozdzielczości/klatkażu, nadpisywanie istniejącego pliku eksportu i bezpośrednie cięcie pliku).

Po mojej akceptacji i wdrożeniu napisz testy dla każdego z formatów eksportu (w tests/ i uruchom run_tests.py), sprawdź wizualnie okno eksportu na zrzucie ekranu, wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki:
   - src/engine/preferences.py (zapis/odczyt stanu projektu i archiwów .bws)
   - src/handlers/autosave_manager.py
   - src/gui/dialogs/unsaved_changes_dialog.py
   - obsługa eksportu/importu projektu, wątku wczytywania, sprawdzania odzyskiwania po starcie oraz zamykania w src/gui/main_window.py
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (duże archiwa `.bws` z osadzonym audio, bezpieczne zapisywanie żeby awaria w połowie nie zniszczyła poprzedniego pliku, przenoszenie projektu `.bws` na inny komputer lub inny dysk, działanie w trybie lokalnym vs w Resolve).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie są skróty przy pakowaniu danych, sprawdzaniu czystego wyjścia albo odbudowie segmentów po wczytaniu)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. fałszywe ostrzeżenie o niezapisanych zmianach albo jego brak po edycji kolorów, odzyskiwanie nieaktualnej sesji, gubienie ścieżki pliku po przeniesieniu projektu)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (co dokładnie ma się zapisywać w `.bws`, kiedy autozapis ma się usuwać i jakie akcje oznaczają „projekt zmieniony”).

Po mojej akceptacji i wdrożeniu napisz testy zapisu, odczytu i odzyskiwania projektów (w tests/ i uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te obszary:
   - installer/src/ (main.rs, engine.rs, state.rs, dialogs.rs, i18n.rs, os/windows.rs, os/linux.rs, os/macos.rs, os/mod.rs)
   - setupfiles/setup.py (sprawdź, kto i kiedy jeszcze z niego korzysta!)
   - skrypty rozruchowe: setupfiles/windows-setup.ps1, setupfiles/linux-setup.sh, setupfiles/mac-setup.sh
   - natywne uruchamiacze i ikony: setupfiles/windows/, setupfiles/linux/, setupfiles/macos/, setupfiles/pe_patcher.py
   - raport/logi_macOS_prawdopodobnie_blad_pobierania_ffmpega.log oraz zgłoszenie GitHub #18 (`gh issue view 18` — uruchamianie `BadWords.exe` i błąd ścieżki)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (zwłaszcza w .github/workflows/, README.md i src/ — nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (blokady SmartScreen/Smart App Control i Apple Gatekeeper, zamykanie okna terminala po uruchomieniu instalatora, pobieranie FFmpeg na wszystkie architektury w tym Apple Silicon, skróty na pulpicie i w menu oraz bezpieczne usuwanie bez kasowania cudzych folderów).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (duplikaty między dwoma instalatorami, ręczne łaty plików wykonywalnych, ścieżki awaryjne)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. błąd pobierania FFmpeg na macOS, problem z zamykaniem terminala, brak lub zepsucie skrótów, ryzyko rozjazdu między instalatorem a aplikacją)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (czy zamykamy i usuwamy stary instalator w Pythonie, jak ma zachowywać się przenoszenie instalacji i pobieranie brakującego Pythona).

Po mojej akceptacji i wdrożeniu sprawdź budowanie i testy instalatora (cargo check i cargo test w folderze installer/ oraz testy w run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i foldery:
   - setupfiles/updater.py
   - src/gui/dialogs/update_dialog.py
   - src/gui/dialogs/v4_migration_dialog.py
   - automatyczne sprawdzanie i ciche aktualizacje w src/main.py oraz src/gui/main_window.py
   - wbudowany przycisk i kod aktualizacji w src/gui/dialogs/settings_dialog.py
   - setupfiles/update-windows.bat, setupfiles/update-linux.sh, setupfiles/update-mac.sh, setupfiles/legacy/, oraz cały folder updaters/
   - raport/raport.md (zgłoszenie testera po aktualizacji z wersji 3 do 4)
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu oraz w .github/workflows/ (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (zabezpieczenie przy wyłączonej samoaktualizacji, brak wymaganej biblioteki certyfikatów SSL na starszych maszynach, zachowanie uprawnień plików po podmianie, odświeżenie skrótów do Resolve po aktualizacji oraz zachowanie przy aktualizacji z wersji 3.x do 4.x).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (gdzie logika aktualizacji jest powielona w kilku plikach i które foldery/skrypty wyglądają na zapomniane duble)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika (np. częściowa aktualizacja zostawiająca zepsute środowisko, ciche aktualizacje bez zgody lub blokujące zamykanie, niespójny wygląd lub brak tłumaczenia przy aktualizacji)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jak ma działać aktualizacja automatyczna vs ręczna, co zrobić z plikami z updaters/ i legacy/, kiedy pokazywać powiadomienie migracyjne).

Po mojej akceptacji i wdrożeniu napisz testy sprawdzania wersji i bezpiecznego uruchamiania aktualizacji (w tests/ i uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
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
1. W 1. kroku NIE edytuj żadnych plików — wykonaj wyłącznie analizę w trybie tylko do odczytu.
2. Przeanalizuj dokładnie te pliki i foldery:
   - src/gui/dialogs/telemetry_popup.py
   - wysyłanie telemetrii w src/engine/preferences.py i wywołanie w src/gui/main_window.py
   - zakładka wsparcia i zgłaszania błędów (w tym pakowanie logów i zrzutów ekranu) w src/gui/dialogs/settings_dialog.py
   - run_tests.py i cały folder tests/
   - .github/workflows/build-installer.yml oraz .github/workflows/installer_test.yml
   - przejrzyj przez `gh issue list --state open`, czy zostały jeszcze jakiekolwiek otwarte zgłoszenia wymagające podpięcia do automatyzacji testów lub zamknięcia.
   Sprawdź wyłącznie bezpośrednie powiązania, wywołania i miejsca styku z wymienionymi wyżej plikami w pozostałych częściach projektu (nie czytaj niepowiązanych plików w całości, żeby nie marnować limitów).
3. Sprawdź spójność między Windows, Linux i macOS (otwieranie folderu z logami na każdym systemie, działanie bez dodatkowych bibliotek sieciowych i certyfikatów, zgodność komunikatów telemetrii we wszystkich językach bez emoji).
4. Przygotuj dla mnie po polsku, prostym językiem bez żargonu i bez kodu, zwięzły raport z 3 sekcjami:
   (A) Co wygląda dziwnie lub podejrzanie (jakie są obejścia przy certyfikatach sieciowych, adresach serwerów lub pomijaniu testów)?
   (B) Co obecnie może się psuć albo działać nieoptymalnie z punktu widzenia użytkownika i właściciela produktu (np. brak prywatności lub zbyt duże logi w zgłoszeniu błędu, otwieranie folderu logów nie działające w części środowisk Linuksa, luki w automatycznych testach przy zmianach w aplikacji)?
   (C) Ponumerowana lista krótkich pytań decyzyjnych do mnie (jakie dane wolno dołączać do paczki błędu, czy automat na GitHubie ma blokować zmiany przy każdym błędzie testów aplikacji).

Po mojej akceptacji i wdrożeniu uzupełnij testy (w tests/ i uruchom run_tests.py), wpisz pełną dokumentację do docs/CEMENTED.md oraz dopisz krótkie 3–4 wyrazowe hasło w .agents/rules/architecture.md (Sekcja 3, limit poniżej 4 000 znaków).
```

---

## Wskazówka końcowa dotycząca kolejności pracy

- **Kolejność ma znaczenie:** Zacznij od Etapu 1 i 2 (fundamenty startu, pliki danych, silnik audio/AI) oraz Punktu 10A–10C (odchudzenie głównego okna) przed głębokim grzebaniem w ekranach edytora i montażu — dzięki temu kolejne sesje będą znacznie szybsze i bezpieczniejsze.
- **Zasada jednego punktu na sesję:** Nie łącz dwóch punktów w jednej rozmowie. Po skończonej sesji upewnij się, że agent zaktualizował wpis w `docs/CEMENTED.md`, krótki wpis w `.agents/rules/architecture.md` (Sekcja 3, poniżej 4 000 znaków) i `docs/DEV_STATE.md` oraz uruchomił pełen komplet testów.
