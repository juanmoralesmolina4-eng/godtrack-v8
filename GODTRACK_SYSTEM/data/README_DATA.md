# GODTRACK DATA ARCHIVE

## carrerer.csv
Este archivo ha sido archivado en la carpeta `data/`.
**Contenido:** Base de datos de nombres de calles (Carrer/Calle).
**Uso:** Actualmente NO es utilizado por el motor de estrategia de carrera (PhysicsEngine), ya que no contiene telemetría (tiempos de vuelta, combustible, etc.).
**Futuro:** Podría utilizarse para generar circuitos urbanos procedurales basándose en nombres reales, pero requiere un adaptador específico.

## Instrucciones
Para importar datos de carrera, asegúrese de usar archivos CSV que contengan columnas como:
- `Lap Time` (Tiempo de Vuelta)
- `S1`, `S2`, `S3` (Sectores)
- `Fuel` (Combustible)
- `Tyre Wear` (Desgaste)
