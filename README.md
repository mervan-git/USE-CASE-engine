# USE-CASE-engine

Lokale Python-app die YouTube-video’s doorzoekt op bruikbare bewegingen, met Gemini fragmenten selecteert en links met begin- en eindtijden categoriseert. Eén algemene bibliotheek; geen klantcase of beoordelingsstap vereist.

## Starten

Vereist: Python 3.9 of nieuwer. Geen externe Python-packages nodig.

```sh
git clone https://github.com/mervan-git/USE-CASE-engine.git
cd USE-CASE-engine
cp .env.example .env
```

Vul de twee API-keys in `.env` in en start:

```sh
python3 engine/server.py
```

Open <http://127.0.0.1:8096/>. Houd het proces actief. De server is uitsluitend lokaal bereikbaar.

**Automatisch zoeken staat standaard aan.** Met ingestelde keys begint na de eerste start een zoekronde; daarna wekelijks. Via Engine-instellingen kun je pauzeren, de frequentie veranderen en limieten instellen.

## Mogelijkheden

- Automatisch wisselende zoekrichtingen: lopen, fietsen, schoonmaken, handwerk, sport, koken, vervoer en producthandelingen.
- Categorisering op actie en camerabeweging.
- Filteren, links kopiëren en fragmenten in de YouTube-speler bekijken.
- SQLite-opslag en hergebruik van zoekresultaten en analyses.
- Registratie van API-aanroepen, tokens en berekende kosten per ronde en fragment.
- Bescherming tegen dubbele taken, overlappende fragmenten en onbeperkte retries.

## Kosten en limieten

Standaard: maximaal vijf nieuwe fragmenten, twee videoanalyses en één zoekopdracht per ronde. Budgetdrempels: $0,10 per ronde en $0,25 per voortschrijdende 24 uur. De engine controleert vóór een volgende aanroep; een lopende aanroep kan een drempel overschrijden. Dit is geen harde factuurlimiet.

Gemini-kosten worden geschat op basis van gerapporteerde input-, output- en denktokens. Tarieven voor Gemini 3.6 Flash zijn vastgelegd op 11 september 2026 in `engine/service.py`; actualiseer deze wanneer tarieven wijzigen. Gratis gebruik kan afwijken van de raming. YouTube-requestaantallen worden apart getoond. Er is geen factuur- of wisselkoersintegratie.

## Beperkingen

- AI-selecties en tijdcodes zijn niet onafhankelijk visueel gecontroleerd.
- De app moet draaien en de computer moet wakker zijn voor geplande rondes.
- Bronvideo’s langer dan tien minuten worden overgeslagen.
- Publieke YouTube-analyse is afhankelijk van Gemini-toegang en beschikbaarheid.
- YouTube-links openen de begintijd; stoppen op de eindtijd werkt via de ingesloten speler waar toegestaan.
- Creatieve geschiktheid geeft geen toestemming om bronmateriaal te hergebruiken.

## Lokale bestanden

API-keys blijven in `.env`. Database en eventuele uploads staan in `work/library/`. Deze bestanden en `outputs/` worden niet naar Git gestuurd. Maak een backup van `work/library/` terwijl de app gestopt is.

Het eerdere opdrachtgerichte CLI-prototype staat in `engine/clips.py`; de hoofdapp start met `engine/server.py`.

## Testen

```sh
python3 -m unittest discover -s engine -p 'test_*.py'
node --check engine/web/app.js
```

Node is alleen nodig voor de optionele JavaScript-syntaxcontrole, niet om de app te draaien. Tests gebruiken tijdelijke databases en geen betaalde API-aanroepen.

## Klantgericht zoeken

Naast automatisch ontdekken is er **+ Klantgericht zoeken**. Bewaar een case met klantnaam, website/productpagina, notities en optioneel oude videolinks of uploads. Kies **Case opslaan** om alleen lokaal te bewaren of **Opslaan & zoeken** om een betaalde zoekronde te starten. Resultaten en kosten zijn per case te bekijken. De algemene ontdek-engine blijft onafhankelijk werken; klantgerichte zoekronden worden handmatig gestart.

Elke resultatenlijst toont maximaal één clip per bronvideo. Nieuwe analyses selecteren het beste passende shot; eerdere bronvideo’s worden binnen dezelfde case overgeslagen. Bestaande dubbele fragmenten blijven voor de historische kostenregistratie bewaard, maar worden niet dubbel getoond. Het aantal resultaten blijft begrensd door het analysebudget: tien verschillende video’s kunnen meer analyses vragen dan tien shots uit één video.

Verbeterde selectie: kandidaten worden vóór betaalde analyse gerangschikt op overeenkomst met de zoekwoorden en videoduur. Kortere, vergelijkbaar relevante video's krijgen voorrang. Niet-publieke, live en niet-insluitbare video's worden overgeslagen. Metadata is alleen een voorselectie; Gemini controleert de zichtbare beweging. Automatische analyses krijgen de gekozen actie expliciet mee. De resultaten tonen een beschrijving en zoekrondes vermelden wanneer de analyselimiet is bereikt. Filters kunnen historische alternatieve shots vinden, met nog steeds één resultaat per bronvideo per lijst.
