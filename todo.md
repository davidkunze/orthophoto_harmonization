**Orthos**
- zur erfassung der tatsächlichen Datenabdeckung wurde bisher "gdal_contour -q -fl 0 -b 1 -f "GPKG" -p" genutzt, mit gdal 3.13 erhält man jedoch nur leere geometrien als ergebnis
  -alternative Numpy?
   
- ~~"path" spalte in kachelübersichtslayer "outline" mit vrt pfad füllen~~
- overviews --> bei mehr als 5 bänder nur übersichten der ersten 5 bänder berechnen
- COG-Berechnung sehr arbeitsspeicherintensiv --> for start einer neuen Kachel, Test, ob ausreichend Arbeitsspeicher zur Verfügung steht
- ~~relative path in vrt  --> https://gis.stackexchange.com/questions/155237/where-vrt-files-store-the-location-of-the-tiles~~
- ~~Kachel-geopackage: relative statt absolute pfade in Attributtabelle~~
- ~~Kachelgröße geteilt durch Pixelgröße ergibt ungerade Zahl (z.B. 2000 m /0,07 m = 28571,43)~~
  - ~~resamplingmethode muss angepasst werden --> nearest neighbour funktioniert nicht, da ungerade Zeile wegelassen wird und somit Leerzeilen/-spalten entstehen~~
  - ~~Y:\David\vrt_cog\resampling_methods~~
- ~~es sollten nur Kacheln berechnet werden, die Daten enthalten, keine Leerkacheln berechnen --> Abgleichen mit Footprint vom VRT?~~
- ~~Fehlerhafte Lückenpixel bei Übersichten der COGs~~
- ~~Overview_Kompression mit JPEG --> Probleme mit 16 Bit Bildern~~
-   ~~Check datatype--> if < 8 bit than JPEG if > 8 bit than andere Overview Kompression~~
- ~~Umprojizieren auf 25832~~
  - ~~Metadatenspalte "epsg" bei Umprojizierung auf 25832 ändern~~
  - ~~Test, ob es sinnvoll ist bei großen Ausgangsdateien zunächst ein Split in Kacheln durchzuführen und dann erst umzuprojirieren~~
    - ~~Nicht umprojizieren in tif, vrt als Zwischenschritt --> sehr schnell --> test bei großen Datensätzen???~~
- ~~aus Metadatenspalte "datum_bildflug_von" Jahr in neue Spalte extrahieren~~
- ~~Nur Kachelstücke mit ID 1 sollen erhalten bleiben~~
- ~~ID-Spalte löschen~~
- ~~.img, .png sollte als Importformat erkannt werden~~
- ~~Ordnerberezeichnung muss angepasst werden~~
  - ~~footprints in eigenen Ordner? Ordnername --> KonGeo~~
- ~~Benennung der Vectorlayer nochmal anpassen~~
- ~~Benennung cog-kacheln anpassen --> Ordnerpfad zu Abkürzungsverzeichnis im Skript aktualisieren~~
- ~~Benennung vrt anpassen --> Ordnerpfad zu Abkürzungsverzeichnis im Skript aktualisieren~~
- ~~Liste mit Kacheln --> Funktion mit erst Rasterkachel- und dann Footprintberechnung~~
- ~~gdal.parseCommandLine mit os.system ersetze~~

**BTK/Colormap Tiffs**
- resampling method sollte so gewählt werden, dass die Rasterzellenwerte ganzzahlig bleiben --> nearest/ mode
