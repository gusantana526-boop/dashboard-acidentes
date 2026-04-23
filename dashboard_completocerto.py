import pandas as pd
import json
import sys
import os
sys.stdout.reconfigure(encoding="utf-8")

print("=" * 50)
print("  Dashboard Acidentes de Trabalho — Brasil")
print("=" * 50)
print("\nCarregando base de dados (pode demorar alguns segundos)...")

csv_path = r"C:\Users\Administrator\Downloads\17458229\data\data\compiled_database\completeDatabase.csv"
# fallback: try with space in folder name
if not os.path.exists(csv_path):
    csv_path = r"C:\Users\Administrator\Downloads\17458229\data\data\compiled database\completeDatabase.csv"
base_dir = os.path.dirname(csv_path)
df = pd.read_csv(csv_path, sep=";", low_memory=False)
print(f"✓ Base carregada: {len(df):,} registros e {df.shape[1]} colunas\n")

# Fix numeric columns
for col in ['DRY BULB TEMPERATURE', 'RELATIVE HUMIDITY', 'WIND SPEED',
            'PRECIPITATION', 'ATMOSPHERIC PRESSURE', 'DEW POINT TEMPERATURE']:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')

print("Processando dados...")

by_year = df['NU_ANO'].value_counts().sort_index()
data_year = {"labels": by_year.index.tolist(), "values": by_year.values.tolist()}

sexo_map = {'M': 'Masculino', 'F': 'Feminino', 'I': 'Ignorado'}
by_sexo = df['CS_SEXO'].map(sexo_map).value_counts()
data_sexo = {"labels": by_sexo.index.tolist(), "values": by_sexo.values.tolist()}

evolucao_map = {
    1.0: 'Cura', 2.0: 'Incap. Temporária', 3.0: 'Incap. Perm. Parcial',
    4.0: 'Incap. Perm. Total', 5.0: 'Óbito (Acidente)', 6.0: 'Óbito (Outras causas)',
    7.0: 'Outro', 9.0: 'Ignorado'
}
by_evolucao = df['EVOLUCAO'].map(evolucao_map).value_counts()
data_evolucao = {"labels": by_evolucao.index.tolist(), "values": by_evolucao.values.tolist()}

by_uf = df['SG_UF_NOT'].value_counts().head(15)
data_uf = {"labels": by_uf.index.tolist(), "values": by_uf.values.tolist()}

temp_year = df.groupby('NU_ANO')['DRY BULB TEMPERATURE'].mean().dropna()
data_temp = {"labels": temp_year.index.tolist(), "values": [round(v,2) for v in temp_year.values.tolist()]}

tipo_map = {1.0: 'Típico', 2.0: 'Trajeto', 9.0: 'Ignorado'}
by_tipo = df['TIPO_ACID'].map(tipo_map).value_counts()
data_tipo = {"labels": by_tipo.index.tolist(), "values": by_tipo.values.tolist()}

corpo_map = {
    '01': 'Olho', '02': 'Cabeça', '03': 'Pescoço', '04': 'Tórax',
    '05': 'Abdômen', '06': 'Mão', '07': 'Membro Superior',
    '08': 'Membro Inferior', '09': 'Pé', '10': 'Corpo Todo', '11': 'Outro', '99': 'Ignorado'
}
df['PART_CORP1'] = df['PART_CORP1'].dropna().astype(int).astype(str).str.zfill(2)
by_corpo = df['PART_CORP1'].map(corpo_map).value_counts().dropna().head(10)
data_corpo = {"labels": by_corpo.index.tolist(), "values": by_corpo.values.tolist()}

temp_vals = df['DRY BULB TEMPERATURE'].dropna()
_, hist_bins = pd.cut(temp_vals, bins=20, retbins=True)
hist_data = pd.cut(temp_vals, bins=hist_bins).value_counts().sort_index()
data_hist_temp = {
    "labels": [f"{iv.left:.1f}–{iv.right:.1f}" for iv in hist_data.index],
    "values": hist_data.values.tolist()
}

by_hora = df['HORA_ACID'].value_counts().sort_index().dropna()
data_hora = {"labels": [int(h) for h in by_hora.index.tolist()], "values": by_hora.values.tolist()}

total = len(df)
obitos = int((df['EVOLUCAO'] == 5.0).sum())
temp_media = round(df['DRY BULB TEMPERATURE'].mean(), 1)
anos = df['NU_ANO'].nunique()

kpis = {
    "total": f"{total:,}".replace(',', '.'),
    "obitos": f"{obitos:,}".replace(',', '.'),
    "temp_media": f"{temp_media}°C",
    "anos": str(anos)
}

all_data = {
    "kpis": kpis,
    "year": data_year,
    "sexo": data_sexo,
    "evolucao": data_evolucao,
    "uf": data_uf,
    "temp": data_temp,
    "tipo": data_tipo,
    "corpo": data_corpo,
    "hist_temp": data_hist_temp,
    "hora": data_hora
}

print("✓ Dados processados\n")
print("Gerando dashboard HTML...")

html = r'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Acidentes de Trabalho — Brasil</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #242836;
    --text: #ece9e4;
    --text2: #a5a0b0;
    --muted: #6b6677;
    --accent: #e8a87c;
    --accent2: #e27d60;
    --accent3: #41b3a3;
    --accent4: #c38d9e;
    --border: #2e3144;
    --border-light: #3a3d54;
    --card-radius: 12px;
    --transition: 0.25s ease-in-out;
  }

  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: "Inter", sans-serif;
    font-weight: 400;
    line-height: 1.6;
    min-height: 100vh;
    overflow-x: hidden;
    -webkit-font-smoothing: antialiased;
  }

  /* Noise overlay */
  .noise-overlay {
    position: fixed;
    inset: 0;
    z-index: 9999;
    pointer-events: none;
    opacity: 0.025;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    background-size: 128px 128px;
  }

  /* Subtle top glow */
  .top-glow {
    position: fixed;
    top: -200px;
    left: 50%;
    transform: translateX(-50%);
    width: 800px;
    height: 400px;
    background: radial-gradient(ellipse, rgba(232,168,124,0.06) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
  }

  /* ===== NAVBAR ===== */
  .navbar {
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.9rem 2rem;
    background: rgba(15,17,23,0.95);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
  }
  .nav-brand {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text2);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .nav-brand .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent2);
  }
  .nav-divider {
    width: 1px;
    height: 16px;
    background: var(--border-light);
    margin: 0 1.2rem;
  }
  .nav-right {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }
  .nav-badge {
    font-size: 0.65rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text2);
    padding: 0.3rem 0.9rem;
    border: 1px solid var(--border);
    border-radius: 6px;
  }

  /* ===== HERO ===== */
  .hero {
    padding: 3rem 2rem 2rem;
    text-align: center;
    position: relative;
    z-index: 1;
  }
  .hero-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1rem;
  }
  .hero-tag-line {
    width: 20px;
    height: 2px;
    background: var(--accent);
    border-radius: 1px;
  }
  .hero-tag-text {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text2);
  }
  .hero-title {
    font-size: clamp(1.6rem, 4.5vw, 3.5rem);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
    color: var(--text);
    margin-bottom: 0.4rem;
  }
  .hero-subtitle {
    font-size: 0.85rem;
    font-weight: 300;
    color: var(--text2);
    letter-spacing: 0.02em;
  }
  .hero-divider {
    width: 100%;
    height: 1px;
    background: var(--border);
    margin-top: 1.8rem;
  }

  /* ===== KPIs ===== */
  .kpis {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: var(--border);
    border: 1px solid var(--border);
    border-radius: var(--card-radius);
    overflow: hidden;
    margin: 1.5rem 2rem;
    position: relative;
    z-index: 1;
  }
  .kpi {
    background: var(--surface);
    padding: 1.4rem 1.2rem;
    text-align: center;
    transition: background var(--transition), box-shadow var(--transition);
    cursor: default;
  }
  .kpi:hover {
    background: var(--surface2);
    box-shadow: inset 0 0 30px rgba(232,168,124,0.04);
  }
  .kpi-label {
    font-size: 0.58rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.5rem;
  }
  .kpi-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--accent);
    line-height: 1.1;
    margin-bottom: 0.3rem;
    transition: transform 0.3s;
  }
  .kpi:hover .kpi-value {
    transform: scale(1.05);
  }
  .kpi-sub {
    font-size: 0.6rem;
    color: var(--muted);
  }

  /* ===== SECTIONS ===== */
  .content {
    padding: 0 2rem 2rem;
    position: relative;
    z-index: 1;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 1rem;
    padding-top: 1.8rem;
  }
  .section-header-bar {
    width: 3px;
    height: 14px;
    background: var(--accent);
    border-radius: 2px;
    flex-shrink: 0;
  }
  .section-title {
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text2);
  }
  .section-header-line {
    flex: 1;
    height: 1px;
    background: var(--border);
  }

  .grid { display: grid; gap: 1rem; margin-bottom: 1rem; }
  .grid-2 { grid-template-columns: 1fr 1fr; }
  .grid-full { grid-template-columns: 1fr; }
  .grid-3-1 { grid-template-columns: 1.8fr 1fr; }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--card-radius);
    padding: 1.3rem 1.5rem 1rem;
    transition: border-color var(--transition), box-shadow var(--transition);
  }
  .card:hover {
    border-color: var(--border-light);
    box-shadow: 0 4px 30px rgba(0,0,0,0.2);
  }
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.8rem;
  }
  .card-title {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text2);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .card-title .bar {
    width: 3px;
    height: 12px;
    background: var(--accent);
    border-radius: 2px;
    flex-shrink: 0;
  }
  .card-expand-btn {
    display: none;
    background: none;
    border: 1px solid var(--border-light);
    color: var(--muted);
    padding: 0.3rem 0.6rem;
    border-radius: 6px;
    font-size: 0.6rem;
    cursor: pointer;
    transition: all var(--transition);
    font-family: "Inter", sans-serif;
  }
  .card-expand-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
  }
  .chart-wrap { position: relative; width: 100%; }
  .chart-wrap canvas { width: 100%; }

  /* Modal de expansao */
  .chart-modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.85);
    z-index: 10000;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }
  .chart-modal-overlay.active {
    display: flex;
  }
  .chart-modal {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--card-radius);
    width: 95vw;
    height: 90vh;
    display: flex;
    flex-direction: column;
    position: relative;
  }
  .chart-modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  .chart-modal-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .chart-modal-close {
    background: none;
    border: 1px solid var(--border-light);
    color: var(--text2);
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    cursor: pointer;
    font-family: "Inter", sans-serif;
    font-size: 0.75rem;
    transition: all var(--transition);
  }
  .chart-modal-close:hover {
    border-color: var(--accent2);
    color: var(--accent2);
  }
  .chart-modal-body {
    flex: 1;
    padding: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .chart-modal-body canvas {
    max-width: 100%;
    max-height: 100%;
  }

  /* ===== FOOTER ===== */
  footer {
    text-align: center;
    padding: 1.5rem 2rem;
    font-size: 0.6rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    border-top: 1px solid var(--border);
    position: relative;
    z-index: 1;
  }

  /* ===== ROTATING BADGE ===== */
  .rotating-badge {
    position: fixed;
    bottom: 1.2rem;
    right: 1.2rem;
    width: 56px;
    height: 56px;
    z-index: 1000;
    opacity: 0.7;
    transition: opacity var(--transition);
  }
  .rotating-badge:hover { opacity: 1; }
  .rotating-badge svg {
    width: 100%;
    height: 100%;
    animation: rotateBadge 14s linear infinite;
  }
  @keyframes rotateBadge {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  /* ===== SCROLL REVEAL ===== */
  .reveal {
    opacity: 0;
    transform: translateY(24px);
    transition: opacity 0.7s ease, transform 0.7s ease;
  }
  .reveal.visible {
    opacity: 1;
    transform: translateY(0);
  }

  @media (max-width: 768px) {
    .reveal {
      opacity: 1;
      transform: translateY(0);
      transition: none;
    }
  }

  /* ===== COUNTER ANIMATION ===== */
  .kpi-value.counting {
    transition: none;
  }

  /* ===== RESPONSIVE ===== */

  /* Tablet */
  @media (max-width: 1024px) {
    .kpis { grid-template-columns: repeat(2, 1fr); margin: 1.2rem 1.5rem; }
    .grid-3-1 { grid-template-columns: 1fr 1fr; }
    .content { padding: 0 1.5rem 1.5rem; }
  }

  @media (max-width: 768px) {
    .navbar { padding: 0.7rem 1rem; }
    .nav-brand { font-size: 0.6rem; }
    .nav-badge { display: none; }
    .hero { padding: 2rem 1rem 1.5rem; }
    .hero-title { font-size: clamp(1.2rem, 5.5vw, 2rem); }
    .hero-subtitle { font-size: 0.75rem; }
    .kpis { margin: 1rem; grid-template-columns: 2fr 2fr; }
    .kpi { padding: 1rem 0.8rem; }
    .kpi-value { font-size: 1.3rem; }
    .content { padding: 0 1rem 1rem; }
    .grid-2 { grid-template-columns: 1fr; }
    .grid-3-1 { grid-template-columns: 1fr; }
    .card { padding: 1rem; }
    .card-header { margin-bottom: 0.6rem; }
    .card-title { font-size: 0.58rem; }
    .card-expand-btn { display: block; }
    .rotating-badge { width: 44px; height: 44px; bottom: 0.8rem; right: 0.8rem; }
  }

  @media (max-width: 480px) {
    .navbar { padding: 0.6rem 0.8rem; }
    .nav-brand { font-size: 0.55rem; }
    .nav-divider { margin: 0 0.6rem; }
    .hero { padding: 1.5rem 0.8rem 1rem; }
    .hero-title { font-size: clamp(1rem, 6vw, 1.6rem); }
    .hero-tag-text { font-size: 0.5rem; }
    .kpis { margin: 0.8rem; gap: 1px; grid-template-columns: 1fr 1fr; }
    .kpi { padding: 0.8rem 0.5rem; }
    .kpi-label { font-size: 0.5rem; }
    .kpi-value { font-size: 1.1rem; }
    .kpi-sub { font-size: 0.5rem; }
    .content { padding: 0 0.6rem 0.8rem; }
    .grid { gap: 0.6rem; }
    .card { padding: 0.8rem; border-radius: 8px; }
    .section-header { padding-top: 1.2rem; }
    .section-title { font-size: 0.52rem; }
    footer { padding: 1rem; font-size: 0.5rem; }
    .rotating-badge { width: 38px; height: 38px; bottom: 0.5rem; right: 0.5rem; }
  }
</style>
</head>
<body>
<div class="noise-overlay"></div>
<div class="top-glow"></div>

<!-- NAVBAR -->
<nav class="navbar">
  <div style="display:flex;align-items:center;">
    <span class="nav-brand"><span class="dot"></span> SINAN</span>
    <div class="nav-divider"></div>
    <span class="nav-brand" style="color:var(--accent);">INMET</span>
  </div>
  <div class="nav-right">
    <span class="nav-badge" id="nav-count">---</span>
  </div>
</nav>

<!-- HERO -->
<header class="hero">
  <div class="hero-tag">
    <span class="hero-tag-line"></span>
    <span class="hero-tag-text">Análise Nacional — Sinan + Inmet</span>
  </div>
  <h1 class="hero-title">Acidentes de Trabalho no Brasil</h1>
  <p class="hero-subtitle">Série histórica completa &middot; 2006 a 2024</p>
  <div class="hero-divider"></div>
</header>

<!-- KPIs -->
<div class="kpis reveal">
  <div class="kpi">
    <div class="kpi-label">Total de Acidentes</div>
    <div class="kpi-value" id="kpi-total">--</div>
    <div class="kpi-sub">Registros notificados</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Óbitos</div>
    <div class="kpi-value" id="kpi-obitos">--</div>
    <div class="kpi-sub">Evolução código 5</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Temperatura Média</div>
    <div class="kpi-value" id="kpi-temp">--</div>
    <div class="kpi-sub">Bulbo seco — Inmet</div>
  </div>
  <div class="kpi">
    <div class="kpi-label">Anos Cobertos</div>
    <div class="kpi-value" id="kpi-anos">--</div>
    <div class="kpi-sub">Série histórica</div>
  </div>
</div>

<!-- CHART: EVOLUCAO ANUAL -->
<div class="content">
  <div class="section-header reveal">
    <span class="section-header-bar"></span>
    <span class="section-title">Evolução Temporal</span>
    <span class="section-header-line"></span>
  </div>
  <div class="grid grid-full reveal">
    <div class="card" data-chart-id="chartYear" data-chart-title="Acidentes Notificados por Ano">
      <div class="card-header">
        <div class="card-title"><span class="bar"></span>Acidentes Notificados por Ano</div>
        <button class="card-expand-btn" aria-label="Expandir grafico">Expandir</button>
      </div>
      <div class="chart-wrap"><canvas id="chartYear"></canvas></div>
    </div>
  </div>

  <!-- CHART: EVOLUCAO + SEXO -->
  <div class="section-header reveal">
    <span class="section-header-bar"></span>
    <span class="section-title">Perfil dos Casos</span>
    <span class="section-header-line"></span>
  </div>
  <div class="grid grid-2 reveal">
    <div class="card" data-chart-id="chartEvolucao" data-chart-title="Desfecho Clínico">
      <div class="card-header">
        <div class="card-title"><span class="bar"></span>Desfecho Clínico</div>
        <button class="card-expand-btn" aria-label="Expandir grafico">Expandir</button>
      </div>
      <div class="chart-wrap"><canvas id="chartEvolucao"></canvas></div>
    </div>
    <div class="card" data-chart-id="chartSexo" data-chart-title="Distribuição por Sexo">
      <div class="card-header">
        <div class="card-title"><span class="bar"></span>Distribuição por Sexo</div>
        <button class="card-expand-btn" aria-label="Expandir grafico">Expandir</button>
      </div>
      <div class="chart-wrap"><canvas id="chartSexo"></canvas></div>
    </div>
  </div>

  <!-- CHART: UF + TIPO -->
  <div class="section-header reveal">
    <span class="section-header-bar"></span>
    <span class="section-title">Geografia e Tipo</span>
    <span class="section-header-line"></span>
  </div>
  <div class="grid grid-3-1 reveal">
    <div class="card" data-chart-id="chartUF" data-chart-title="Top 15 Estados">
      <div class="card-header">
        <div class="card-title"><span class="bar"></span>Top 15 Estados</div>
        <button class="card-expand-btn" aria-label="Expandir grafico">Expandir</button>
      </div>
      <div class="chart-wrap"><canvas id="chartUF"></canvas></div>
    </div>
    <div class="card" data-chart-id="chartTipo" data-chart-title="Tipo de Acidente">
      <div class="card-header">
        <div class="card-title"><span class="bar"></span>Tipo de Acidente</div>
        <button class="card-expand-btn" aria-label="Expandir grafico">Expandir</button>
      </div>
      <div class="chart-wrap"><canvas id="chartTipo"></canvas></div>
    </div>
  </div>

  <!-- CHART: TEMP ANO + HORA -->
  <div class="section-header reveal">
    <span class="section-header-bar"></span>
    <span class="section-title">Variáveis Ambientais</span>
    <span class="section-header-line"></span>
  </div>
  <div class="grid grid-2 reveal">
    <div class="card" data-chart-id="chartTemp" data-chart-title="Temperatura Média por Ano">
      <div class="card-header">
        <div class="card-title"><span class="bar"></span>Temperatura Média por Ano</div>
        <button class="card-expand-btn" aria-label="Expandir grafico">Expandir</button>
      </div>
      <div class="chart-wrap"><canvas id="chartTemp"></canvas></div>
    </div>
    <div class="card" data-chart-id="chartHora" data-chart-title="Distribuição por Hora do Dia">
      <div class="card-header">
        <div class="card-title"><span class="bar"></span>Distribuição por Hora do Dia</div>
        <button class="card-expand-btn" aria-label="Expandir grafico">Expandir</button>
      </div>
      <div class="chart-wrap"><canvas id="chartHora"></canvas></div>
    </div>
  </div>

  <!-- CHART: HIST TEMP + CORPO -->
  <div class="section-header reveal">
    <span class="section-header-bar"></span>
    <span class="section-title">Distribuições</span>
    <span class="section-header-line"></span>
  </div>
  <div class="grid grid-2 reveal" style="margin-bottom:2rem;">
    <div class="card" data-chart-id="chartHistTemp" data-chart-title="Temperatura no Momento do Acidente">
      <div class="card-header">
        <div class="card-title"><span class="bar"></span>Temperatura no Momento do Acidente</div>
        <button class="card-expand-btn" aria-label="Expandir grafico">Expandir</button>
      </div>
      <div class="chart-wrap"><canvas id="chartHistTemp"></canvas></div>
    </div>
    <div class="card" data-chart-id="chartCorpo" data-chart-title="Partes do Corpo Mais Afetadas">
      <div class="card-header">
        <div class="card-title"><span class="bar"></span>Partes do Corpo Mais Afetadas</div>
        <button class="card-expand-btn" aria-label="Expandir grafico">Expandir</button>
      </div>
      <div class="chart-wrap"><canvas id="chartCorpo"></canvas></div>
    </div>
  </div>
</div>

<!-- CHART MODAL -->
<div class="chart-modal-overlay" id="chartModal">
  <div class="chart-modal">
    <div class="chart-modal-header">
      <span class="chart-modal-title" id="chartModalTitle"></span>
      <button class="chart-modal-close" id="chartModalClose">Fechar</button>
    </div>
    <div class="chart-modal-body"><canvas id="chartModalCanvas"></canvas></div>
  </div>
</div>

<!-- BADGE -->
<div class="rotating-badge">
  <svg viewBox="0 0 64 64">
    <circle cx="32" cy="32" r="28" fill="none" stroke="#2e3144" stroke-width="1"/>
    <path id="badgePath" fill="none" stroke="none" d="M32,4 A28,28 0 1,1 31.99,4"/>
    <text font-size="7.5" font-weight="700" fill="#6b6677" font-family="Inter,sans-serif" letter-spacing="1.5">
      <textPath href="#badgePath">SINAN &bull; INMET &bull; SINAN &bull; INMET &bull;</textPath>
    </text>
  </svg>
</div>

<footer>
  Base Sinan &middot; Inmet &middot; 2006–2024
</footer>

<script>
const DATA = __JSONDATA__;

/* KPIs with counting animation */
function animateCount(el, target, duration) {
  const start = 0;
  const startTime = performance.now();
  function update(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeOut = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + (target - start) * easeOut);
    el.textContent = current.toLocaleString("pt-BR");
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

const kpiEl = document.getElementById("kpi-total");
const obitoEl = document.getElementById("kpi-obitos");
document.getElementById("kpi-temp").textContent = DATA.kpis.temp_media;
document.getElementById("kpi-anos").textContent = DATA.kpis.anos;
const totalNum = parseInt(DATA.kpis.total.replace(/[.\s]/g, "")) || 0;
const obitNum = parseInt(DATA.kpis.obitos.replace(/[.\s]/g, "")) || 0;
animateCount(kpiEl, totalNum, 1800);
animateCount(obitoEl, obitNum, 2200);

document.getElementById("nav-count").textContent = DATA.kpis.total + " registros";

/* Chart.js global defaults */
Chart.defaults.font.family = "Inter, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.font.weight = 400;

// Shared configs
const GRID = { color: "rgba(46,49,68,0.5)", drawBorder: false, lineWidth: 0.5 };
const GRID_X = { color: "rgba(46,49,68,0.3)", drawBorder: false, lineWidth: 0.5 };
const GRID_NONE = { display: false };
const TT_CONFIG = {
  backgroundColor: "#1a1d27",
  borderColor: "#2e3144",
  borderWidth: 1,
  titleColor: "#ece9e4",
  titleFont: { size: 12, weight: 600 },
  bodyColor: "#a5a0b0",
  bodyFont: { size: 11, weight: 400 },
  padding: { top: 10, right: 12, bottom: 10, left: 12 },
  cornerRadius: 8,
  displayColors: true,
  boxPadding: 4,
};
const TICK_X = { font: { size: 10, weight: 400 }, color: "#6b6677", padding: 8 };
const TICK_Y = { font: { size: 9, weight: 400 }, color: "#6b6677", padding: 4 };
const tickY_k = { ...TICK_Y, callback: v => v >= 1000 ? (v/1000).toFixed(0) + "k" : v };

function baseScales() {
  return {
    x: { grid: GRID_X, ticks: TICK_X },
    y: { grid: GRID, ticks: tickY_k }
  };
}
function baseScalesNoGridY() {
  return {
    x: { grid: GRID_X, ticks: TICK_X },
    y: { grid: GRID_NONE, ticks: tickY_k }
  };
}

function tooltipNum(label) {
  return function(ctx) { return ctx.parsed[label].toLocaleString("pt-BR"); };
}

/* Color palettes */
const DOUGHNUT_C = ["#e8a87c","#41b3a3","#c38d9e","#e27d60","#a5a0b0","#6b6677","#f5c469","#6d8299"];

/* ===== CHART: EVOLUÇÃO ANUAL ===== */
new Chart(document.getElementById("chartYear"), {
  type: "bar",
  data: {
    labels: DATA.year.labels,
    datasets: [{
      label: "Acidentes",
      data: DATA.year.values,
      backgroundColor: function(context) {
        const chart = context.chart;
        const {ctx: c, chartArea} = chart;
        if (!chartArea) return "#e27d60";
        const gradient = c.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
        gradient.addColorStop(0, "rgba(226,125,96,0.4)");
        gradient.addColorStop(0.5, "rgba(232,168,124,0.7)");
        gradient.addColorStop(1, "rgba(245,196,105,0.9)");
        return gradient;
      },
      borderColor: "rgba(232,168,124,0.3)",
      borderWidth: 0,
      borderRadius: { topRight: 4, topLeft: 4 },
      hoverBackgroundColor: "#e27d60",
      hoverBorderColor: "#e27d60",
      hoverBorderWidth: 1,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 1200, easing: "easeOutQuart" },
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { display: false },
      tooltip: {
        ...TT_CONFIG,
        callbacks: {
          title: ctx => "Ano " + ctx[0].label,
          label: ctx => "  " + ctx.parsed.y.toLocaleString("pt-BR") + " acidentes"
        }
      }
    },
    scales: baseScales()
  }
});

/* ===== CHART: EVOLUÇÃO (Desfecho) ===== */
new Chart(document.getElementById("chartEvolucao"), {
  type: "doughnut",
  data: {
    labels: DATA.evolucao.labels,
    datasets: [{
      data: DATA.evolucao.values,
      backgroundColor: DOUGHNUT_C.slice(0, DATA.evolucao.labels.length),
      borderWidth: 2,
      borderColor: "#1a1d27",
      hoverOffset: 8,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 1400, easing: "easeOutQuart" },
    cutout: "55%",
    plugins: {
      legend: {
        display: true,
        position: "right",
        align: "center",
        labels: {
          font: { size: 10, weight: 400 },
          color: "#a5a0b0",
          padding: 6,
          boxWidth: 8,
          boxHeight: 8,
          useBorderRadius: true,
          borderRadius: 2,
        }
      },
      tooltip: {
        ...TT_CONFIG,
        callbacks: {
          label: ctx => {
            const total = ctx.dataset.data.reduce((a,b) => a + b, 0);
            const pct = ((ctx.parsed / total) * 100).toFixed(1);
            return " " + ctx.label + ": " + ctx.parsed.toLocaleString("pt-BR") + " (" + pct + "%)";
          }
        }
      }
    }
  }
});

/* ===== CHART: SEXO ===== */
new Chart(document.getElementById("chartSexo"), {
  type: "doughnut",
  data: {
    labels: DATA.sexo.labels,
    datasets: [{
      data: DATA.sexo.values,
      backgroundColor: ["#41b3a3","#c38d9e","#6b6677"],
      borderWidth: 2,
      borderColor: "#1a1d27",
      hoverOffset: 8,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 1400, easing: "easeOutQuart" },
    cutout: "55%",
    plugins: {
      legend: {
        display: true,
        position: "bottom",
        labels: {
          font: { size: 11, weight: 400 },
          color: "#a5a0b0",
          padding: 14,
          boxWidth: 10,
          boxHeight: 10,
          useBorderRadius: true,
          borderRadius: 2,
        }
      },
      tooltip: {
        ...TT_CONFIG,
        callbacks: {
          label: ctx => {
            const total = ctx.dataset.data.reduce((a,b) => a + b, 0);
            const pct = ((ctx.parsed / total) * 100).toFixed(1);
            return " " + ctx.label + ": " + ctx.parsed.toLocaleString("pt-BR") + " (" + pct + "%)";
          }
        }
      }
    }
  }
});

/* ===== CHART: ESTADOS (Horizontal Bar) ===== */
const ufNames = {35:"SP",43:"RS",41:"PR",31:"MG",42:"SC",52:"GO",29:"BA",33:"RJ",50:"MS",23:"CE",51:"MT",26:"PE",21:"MA",53:"DF",11:"RO"};
new Chart(document.getElementById("chartUF"), {
  type: "bar",
  data: {
    labels: DATA.uf.labels.map(c => ufNames[parseInt(c)] || c),
    datasets: [{
      label: "Acidentes",
      data: DATA.uf.values,
      backgroundColor: "#41b3a3",
      borderColor: "rgba(65,179,163,0.4)",
      borderWidth: 0,
      borderRadius: { topRight: 4, topLeft: 4 },
      hoverBackgroundColor: "#38a898",
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 1200, easing: "easeOutQuart" },
    indexAxis: "x",
    plugins: {
      legend: { display: false },
      tooltip: {
        ...TT_CONFIG,
        callbacks: {
          title: ctx => { const idx = ctx[0].dataIndex; return DATA.uf.labels[idx] + " (" + ufNames[parseInt(DATA.uf.labels[idx])] + ")"; },
          label: ctx => "  " + ctx.parsed.y.toLocaleString("pt-BR") + " acidentes"
        }
      }
    },
    scales: baseScales()
  }
});

/* ===== CHART: TIPO ===== */
new Chart(document.getElementById("chartTipo"), {
  type: "doughnut",
  data: {
    labels: DATA.tipo.labels,
    datasets: [{
      data: DATA.tipo.values,
      backgroundColor: ["#e27d60","#c38d9e","#6b6677"],
      borderWidth: 2,
      borderColor: "#1a1d27",
      hoverOffset: 8,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 1400, easing: "easeOutQuart" },
    cutout: "55%",
    plugins: {
      legend: {
        display: true,
        position: "bottom",
        labels: {
          font: { size: 11, weight: 400 },
          color: "#a5a0b0",
          padding: 14,
          boxWidth: 10,
          boxHeight: 10,
          useBorderRadius: true,
          borderRadius: 2,
        }
      },
      tooltip: {
        ...TT_CONFIG,
        callbacks: {
          label: ctx => {
            const total = ctx.dataset.data.reduce((a,b) => a + b, 0);
            const pct = ((ctx.parsed / total) * 100).toFixed(1);
            return " " + ctx.label + ": " + ctx.parsed.toLocaleString("pt-BR") + " (" + pct + "%)";
          }
        }
      }
    }
  }
});

/* ===== CHART: TEMPERATURA POR ANO ===== */
new Chart(document.getElementById("chartTemp"), {
  type: "line",
  data: {
    labels: DATA.temp.labels,
    datasets: [{
      label: "Temp. Média",
      data: DATA.temp.values,
      borderColor: "#c38d9e",
      backgroundColor: "rgba(195,141,158,0.08)",
      borderWidth: 2.5,
      pointRadius: 4,
      pointBackgroundColor: "#c38d9e",
      pointBorderColor: "#1a1d27",
      pointBorderWidth: 2,
      pointHoverRadius: 7,
      pointHoverBackgroundColor: "#c38d9e",
      pointHoverBorderColor: "#fff",
      pointHoverBorderWidth: 2,
      fill: true,
      tension: 0.4,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 1400, easing: "easeOutQuart" },
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { display: false },
      tooltip: {
        ...TT_CONFIG,
        callbacks: {
          title: ctx => "Ano " + ctx[0].label,
          label: ctx => "  Média: " + ctx.parsed.y + "°C"
        }
      }
    },
    scales: {
      x: { grid: GRID_X, ticks: TICK_X },
      y: {
        grid: GRID,
        ticks: { ...TICK_Y, callback: v => v + "°C" }
      }
    }
  }
});

/* ===== CHART: HORA DO DIA ===== */
const dayLabels = DATA.hora.labels.map(h => String(h).padStart(2,"0") + "h");
new Chart(document.getElementById("chartHora"), {
  type: "bar",
  data: {
    labels: dayLabels,
    datasets: [{
      label: "Acidentes",
      data: DATA.hora.values,
      backgroundColor: DATA.hora.labels.map((h, i) => {
        if (h >= 6 && h <= 17) return "#e27d60";
        if (h >= 18 && h <= 22) return "#c38d9e";
        return "rgba(65,179,163,0.35)";
      }),
      borderWidth: 0,
      borderRadius: { topRight: 3, topLeft: 3 },
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 1000, easing: "easeOutQuart" },
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { display: false },
      tooltip: {
        ...TT_CONFIG,
        callbacks: {
          title: ctx => ctx[0].label + " horas",
          label: ctx => "  " + ctx.parsed.y.toLocaleString("pt-BR") + " acidentes"
        }
      }
    },
    scales: baseScales()
  }
});

/* ===== CHART: HISTOGRAMA TEMPERATURA ===== */
new Chart(document.getElementById("chartHistTemp"), {
  type: "bar",
  data: {
    labels: DATA.hist_temp.labels,
    datasets: [{
      data: DATA.hist_temp.values,
      backgroundColor: DATA.hist_temp.values.map((v, i) => {
        const t = i / DATA.hist_temp.values.length;
        if (t < 0.3) return "rgba(65,179,163,0.45)";
        if (t < 0.5) return "rgba(232,168,124,0.55)";
        if (t < 0.65) return "rgba(226,125,96,0.35)";
        return "rgba(46,49,68,0.5)";
      }),
      borderColor: "#41b3a3",
      borderWidth: 0.5,
      borderRadius: { topRight: 3, topLeft: 3 },
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 1400, easing: "easeOutQuart" },
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { display: false },
      tooltip: {
        ...TT_CONFIG,
        callbacks: {
          label: ctx => "  " + ctx.parsed.y.toLocaleString("pt-BR") + " acidentes"
        }
      }
    },
    scales: {
      x: {
        grid: GRID_X,
        ticks: { maxRotation: 45, minRotation: 45, font: { size: 8, weight: 400 }, color: "#6b6677" }
      },
      y: { grid: GRID, ticks: tickY_k }
    }
  }
});

/* ===== CHART: PARTES DO CORPO ===== */
new Chart(document.getElementById("chartCorpo"), {
  type: "bar",
  data: {
    labels: DATA.corpo.labels,
    datasets: [{
      data: DATA.corpo.values,
      backgroundColor: "#c38d9e",
      borderColor: "rgba(195,141,158,0.4)",
      borderWidth: 0,
      borderRadius: { topRight: 3, topLeft: 3 },
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    animation: { duration: 1200, easing: "easeOutQuart" },
    indexAxis: "y",
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { display: false },
      tooltip: {
        ...TT_CONFIG,
        callbacks: { label: ctx => "  " + ctx.parsed.x.toLocaleString("pt-BR") + " casos" }
      }
    },
    scales: {
      x: {
        grid: GRID,
        ticks: { color: "#6b6677", font: { size: 9, weight: 400 }, callback: v => v >= 1000 ? (v/1000).toFixed(0)+"k" : v }
      },
      y: {
        grid: { display: false },
        ticks: { color: "#a5a0b0", font: { size: 10, weight: 400 } }
      }
    }
  }
});

/* ===== CHART MODAL (Mobile Expand) ===== */
const modalEl = document.getElementById("chartModal");
const modalTitleEl = document.getElementById("chartModalTitle");
const modalCloseEl = document.getElementById("chartModalClose");
const modalCanvas = document.getElementById("chartModalCanvas");
let modalChart = null;

function openModal(chartId, title) {
  const srcCanvas = document.getElementById(chartId);
  if (!srcCanvas) return;
  const srcChart = Chart.getChart(srcCanvas);
  if (!srcChart) return;
  modalTitleEl.textContent = title;
  modalEl.classList.add("active");
  document.body.style.overflow = "hidden";

  // Destroy previous modal chart
  if (modalChart) { modalChart.destroy(); modalChart = null; }

  const cfg = {
    type: srcChart.config.type,
    data: JSON.parse(JSON.stringify(srcChart.config.data)),
    options: JSON.parse(JSON.stringify(srcChart.config.options))
  };

  // Scale up fonts for fullscreen
  if (cfg.options && cfg.options.plugins && cfg.options.plugins.legend) {
    const legend = cfg.options.plugins.legend;
    if (legend.labels && legend.labels.font) {
      if (typeof legend.labels.font === 'object') legend.labels.font.size = Math.max(13, legend.labels.font.size + 3);
    }
  }

  // Render new chart on modal canvas
  setTimeout(() => {
    const ChartClass = srcChart.constructor;
    modalChart = new ChartClass(modalCanvas, cfg);
    setTimeout(() => modalChart && modalChart.resize(), 60);
  }, 100);
}

function closeModal() {
  modalEl.classList.remove("active");
  document.body.style.overflow = "";
  if (modalChart) { modalChart.destroy(); modalChart = null; }
}

document.querySelectorAll(".card-expand-btn").forEach(btn => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const card = btn.closest(".card");
    if (!card) return;
    openModal(card.dataset.chartId, card.dataset.chartTitle);
  });
});

modalCloseEl.addEventListener("click", closeModal);
modalEl.addEventListener("click", (e) => {
  if (e.target === modalEl) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && modalEl.classList.contains("active")) closeModal();
});

/* ===== SCROLL REVEAL ===== */
const reveals = document.querySelectorAll(".reveal");
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add("visible");
      observer.unobserve(e.target);
    }
  });
}, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
reveals.forEach(el => observer.observe(el));
</script>
</body>
</html>'''

html_final = html.replace("__JSONDATA__", json.dumps(all_data, ensure_ascii=False))

with open(os.path.join(base_dir, "dashboard_acidentes.html"), "w", encoding="utf-8") as f:
    f.write(html_final)

print("✓ Dashboard gerado: dashboard_acidentes.html")
print("\nAbra o arquivo dashboard_acidentes.html no seu navegador!")
print("=" * 50)
