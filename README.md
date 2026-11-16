# Simulace šíření samizdatu v Praze

## Spuštění

Potřeba je Python 3.10 nebo novější.

```
pip install -r requirements.txt
python simulace.py
```

(Na macOS/Linuxu případně `pip3` a `python3`.)

Nejdřív se otevře okno **Settings**, kde jdou upravit parametry (počet lidí, dosahy, váhy…).
Po stisknutí **Start** se otevře mapa Prahy s animací a graf počtu lidí v jednotlivých rolích.
Mezerník = pauza / pokračovat.

## Soubory

- `simulace.py` – simulace, nastavení a animace
- `praha.py` – mapa Prahy (22 správních obvodů) a náhodné rozmístění lidí podle počtu obyvatel
- `praha_obvody.json` – hranice obvodů

## Zdroje dat

- Hranice obvodů: ČÚZK, RÚIAN
- Počty obyvatel: ČSÚ, stav k 31. 12. 2023
