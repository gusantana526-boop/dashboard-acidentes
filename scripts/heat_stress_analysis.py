import pandas as pd
import numpy as np
import json, os, time

CSV_PATH = 'data/compiled/completeDatabase.csv'
OUTPUT_PATH = 'data/compiled/heat_stress_bands.json'
CHUNKSIZE = 200_000

CLIMATE_COLS = [
    'DRY BULB TEMPERATURE',
    'RELATIVE HUMIDITY',
    'WIND SPEED',
    'DEW POINT TEMPERATURE'
]

BANDS = {
    'ET':  {'I': (-3.64, 4.23), 'II': (4.23, 12.1), 'III': (12.1, 19.9), 'IV': (19.9, 27.7), 'V': (27.7, 35.6)},
    'DI':  {'I': (-3.64, 4.21), 'II': (4.21, 12),   'III': (12, 19.8),   'IV': (19.8, 27.6), 'V': (27.6, 35.5)},
    'HI':  {'I': (-26.8, 16.1), 'II': (16.1, 58.8), 'III': (58.8, 102),  'IV': (102, 144),   'V': (144, 187)},
    'ETW': {'I': (-19.2, -4.58),'II': (-4.58, 9.96),'III': (9.96, 24.5), 'IV': (24.5, 39.1), 'V': (39.1, 53.7)},
    'HX':  {'I': (-6.62, 7.12), 'II': (7.12, 20.8), 'III': (20.8, 34.5), 'IV': (34.5, 48.2), 'V': (48.2, 61.9)},
    'AT':  {'I': (-3.61, 6.02), 'II': (6.02, 15.6), 'III': (15.6, 25.2), 'IV': (25.2, 34.8), 'V': (34.8, 44.5)},
    'MDI': {'I': (0.6, 7.6),    'II': (7.6, 14.6),  'III': (14.6, 21.5), 'IV': (21.5, 28.5), 'V': (28.5, 35.5)},
    'WCT': {'I': (-7.64, 3.21), 'II': (3.21, 14),   'III': (14, 24.8),   'IV': (24.8, 35.6), 'V': (35.6, 46.4)}
}

BAND_LABELS = ['I', 'II', 'III', 'IV', 'V']
BAND_EDGES = {}
for idx, bands in BANDS.items():
    edges = [bands[l][0] for l in BAND_LABELS] + [bands['V'][1]]
    BAND_EDGES[idx] = np.array(edges)

def classify_vector(values, edges):
    indices = np.digitize(values, edges, right=False) - 1
    indices = np.clip(indices, 0, 4)
    return indices  # 0=I, 1=II, 2=III, 3=IV, 4=V

def wet_bulb_stull(T, RH):
    return (T * np.arctan(0.151977 * np.sqrt(RH + 8.313659))
            + np.arctan(T + RH) - np.arctan(RH - 1.676331)
            + 0.00391838 * RH**1.5 * np.arctan(0.023101 * RH)
            - 4.686035)

def compute_indices(df):
    T = df['DRY BULB TEMPERATURE'].to_numpy(dtype=float)
    RH = df['RELATIVE HUMIDITY'].to_numpy(dtype=float)
    WS = df['WIND SPEED'].to_numpy(dtype=float)
    TD = df['DEW POINT TEMPERATURE'].to_numpy(dtype=float)

    out = {}

    Tbu = wet_bulb_stull(T, RH)
    out['ET'] = 0.4 * (T + Tbu) + 4.8

    out['DI'] = T - 0.55 * (1 - 0.01 * RH) * (T - 14.5)

    T_F = T * 9/5 + 32
    hi_F = (-42.379 + 2.04901523*T_F + 10.14333127*RH
            - 0.22475541*T_F*RH - 0.00683783*T_F**2
            - 0.05481717*RH**2 + 0.00122874*T_F**2*RH
            + 0.00085282*T_F*RH**2 - 0.00000199*T_F**2*RH**2)
    out['HI'] = (hi_F - 32) * 5/9

    out['HX'] = T + 0.5555 * (6.11 * np.exp(5417.7530 * (1/273.16 - 1/(273.16 + TD))) - 10)

    T_K = T + 273.16
    e = 6.105 * np.exp(25.22 * (T_K - 273.16) / T_K - 5.31 * np.log(T_K / 273.16))
    out['AT'] = -2.7 + 1.04*T + 2.0*e - 0.65*WS

    out['ETW'] = (T * np.arctan(0.151977 * np.sqrt(RH + 8.313659))
                  + np.arctan(T + RH) - np.arctan(RH - 1.676331)
                  + 0.00391838 * RH**1.5 * np.arctan(0.023101 * RH)
                  - 4.686035 - 0.4 * WS)

    out['MDI'] = 0.75*T + 0.3*TD

    V_kmh = WS * 3.6
    wct = np.where((T <= 10) & (V_kmh >= 4.8),
                   13.12 + 0.6215*T - 11.37*V_kmh**0.16 + 0.3965*T*V_kmh**0.16, T)
    out['WCT'] = wct

    return out

def process():
    print(f"Processing {CSV_PATH} in chunks of {CHUNKSIZE:,} rows...")

    # Count total rows (header excluded) for progress
    import subprocess
    result = subprocess.run(['findstr', '/R', '/N', '^', CSV_PATH], capture_output=True, text=True, shell=True)
    total_rows = 0
    try:
        total_rows = int(result.stdout.strip().split(':')[0])
    except:
        pass

    reader = pd.read_csv(CSV_PATH, sep=';', decimal=',', na_values=['NA'],
                         usecols=CLIMATE_COLS, chunksize=CHUNKSIZE,
                         encoding='utf-8-sig', low_memory=False)

    counters = {idx: np.zeros(5, dtype=np.int64) for idx in BANDS}
    total_valid = 0
    chunk_i = 0

    t0 = time.time()
    for chunk in reader:
        chunk_i += 1
        initial = len(chunk)

        # Drop rows with any missing climate value
        chunk = chunk.dropna()
        valid = len(chunk)

        if valid == 0:
            print(f"  Chunk {chunk_i}: {initial:,} rows, all skipped (NA)")
            continue

        indices = compute_indices(chunk)

        for idx in BANDS:
            cls = classify_vector(indices[idx], BAND_EDGES[idx])
            for b in range(5):
                counters[idx][b] += int(np.sum(cls == b))

        total_valid += valid
        elapsed = time.time() - t0
        rate = total_valid / elapsed if elapsed > 0 else 0
        print(f"  Chunk {chunk_i}: {initial:,} rows ({valid:,} valid) | "
              f"Total: {total_valid:,} | {rate:,.0f} rows/s")

    # Build result as percentages
    result = {}
    for idx in BANDS:
        counts = counters[idx]
        total = counts.sum()
        if total > 0:
            pcts = {band: round(float(counts[i]) / total * 100, 1)
                    for i, band in enumerate(BAND_LABELS)}
        else:
            pcts = {band: 0.0 for band in BAND_LABELS}
        result[idx] = pcts

    print(f"\nDone! Processed {total_valid:,} valid rows in {time.time()-t0:.1f}s")
    print(json.dumps(result, indent=2))

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {OUTPUT_PATH}")

if __name__ == '__main__':
    process()
