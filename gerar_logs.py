import numpy as np
from scipy.signal import butter, filtfilt


def calcular_todas_metricas(sinal_real, sinal_modelo):
    """
    Calcula as 3 principais métricas de validação de modelos:
    - MAE: Erro Absoluto Médio (diferença média na unidade original)
    - RMSE: Raiz do Erro Quadrático Médio (pune desvios e picos)
    - NMAE: Erro Normalizado (percentual do fundo de escala, fidelidade visual)
    """
    erro = sinal_real - sinal_modelo

    mae = np.mean(np.abs(erro))
    rmse = np.sqrt(np.mean(erro**2))

    fundo_de_escala = np.max(np.abs(sinal_real))
    if fundo_de_escala < 1e-5:
        nmae = 0.0
    else:
        nmae = (mae / fundo_de_escala) * 100.0

    return mae, rmse, nmae


def estatisticas_sinal(sinal):
    """
    Retorna estatísticas descritivas completas de um sinal:
    mínimo, máximo, faixa (range), média e desvio padrão.
    Usadas para reportar a base de normalização do NMAE e
    documentar a faixa de operação de cada variável no ensaio.
    """
    return {
        "min": np.min(sinal),
        "max": np.max(sinal),
        "range": np.max(sinal) - np.min(sinal),
        "media": np.mean(sinal),
        "desvio_padrao": np.std(sinal),
    }


def calcular_metricas_do_arquivo(caminho_arquivo="dados_ensaio_NATURAL.npz"):
    print(f"Carregando dados de: {caminho_arquivo}...")

    try:
        dados = np.load(caminho_arquivo)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        return

    t_hw = dados['tempos_hardware_fisico']
    t_sim = dados['tempos_simulacao_digital']

    if len(t_hw) == 0 or len(t_sim) == 0:
        print("Dados insuficientes no arquivo para calcular métricas.")
        return

    # --- Alinhamento temporal (interpola sinais do Twin na base de tempo do HW) ---
    def interpolar_twin_para_hw(sinal_twin):
        return np.interp(t_hw, t_sim, sinal_twin)

    # --- Filtro passa-baixas para os sinais medidos no hardware (ruído de sensor) ---
    passo_hardware_estimado = np.mean(np.diff(t_hw))
    fs = 1.0 / passo_hardware_estimado
    nyq = 0.5 * fs
    fc = 1.0 / (2 * np.pi * 0.1)
    wn = min(fc / nyq, 0.99)
    b, a = butter(2, wn, btype='low')

    torques_brutos = dados['torques_medidos_sensor_nm']
    potencias_brutas = dados['potencias_medidas_sensor']

    torques_filtrados = filtfilt(b, a, torques_brutos)
    potencias_filtradas = filtfilt(b, a, potencias_brutas)

    # --- Sinais do Gêmeo Digital, alinhados ao tempo do hardware ---
    rpm_twin_interp = interpolar_twin_para_hw(dados['velocidades_angulares_gerador_digital'])
    torque_twin_interp = interpolar_twin_para_hw(dados['torques_no_eixo_digital'])
    pot_twin_interp = interpolar_twin_para_hw(dados['potencias_gerada'])

    rpm_real = dados['velocidades_angulares_reais_rpm']

    # ---> CÁLCULO DAS MÉTRICAS DE ERRO <---
    mae_rpm, rmse_rpm, nmae_rpm = calcular_todas_metricas(rpm_real, rpm_twin_interp)
    mae_torq, rmse_torq, nmae_torq = calcular_todas_metricas(torques_filtrados, torque_twin_interp)
    mae_pot, rmse_pot, nmae_pot = calcular_todas_metricas(potencias_filtradas, pot_twin_interp)

    # ---> ESTATÍSTICAS DESCRITIVAS (min/max/faixa) DE CADA VARIÁVEL <---
    stats_rpm = estatisticas_sinal(rpm_real)
    stats_torq = estatisticas_sinal(torques_filtrados)
    stats_pot = estatisticas_sinal(potencias_filtradas)
    stats_vento = estatisticas_sinal(dados['velocidades_vento_m_s_hw'])

    duracao_ensaio = t_hw[-1] - t_hw[0]

    # =========================================================================
    # LOG COMPLETO
    # =========================================================================
    print("\n" + "=" * 88)
    print("=== RELATÓRIO DE VALIDAÇÃO: EMULADOR VS GÊMEO DIGITAL ===")
    print("=" * 88)
    print(f"Duração do ensaio: {duracao_ensaio:.2f} s | Amostras HW: {len(t_hw)} | Amostras Sim: {len(t_sim)}")
    print(f"Passo de hardware estimado: {passo_hardware_estimado * 1000:.2f} ms")

    print("\n--- FAIXA DE OPERAÇÃO DAS VARIÁVEIS (sinal real/medido) ---")
    print("-" * 88)
    print(f"{'Variável':<12} | {'Mín':>10} | {'Máx':>10} | {'Faixa (range)':>14} | {'Média':>10} | {'Desv. Padrão':>13}")
    print("-" * 88)
    print(f"{'Vento':<12} | {stats_vento['min']:>7.2f} m/s | {stats_vento['max']:>7.2f} m/s | "
          f"{stats_vento['range']:>11.2f} m/s | {stats_vento['media']:>7.2f} m/s | {stats_vento['desvio_padrao']:>10.2f} m/s")
    print(f"{'RPM':<12} | {stats_rpm['min']:>7.2f} RPM | {stats_rpm['max']:>7.2f} RPM | "
          f"{stats_rpm['range']:>11.2f} RPM | {stats_rpm['media']:>7.2f} RPM | {stats_rpm['desvio_padrao']:>10.2f} RPM")
    print(f"{'Torque':<12} | {stats_torq['min']:>7.2f} N.m | {stats_torq['max']:>7.2f} N.m | "
          f"{stats_torq['range']:>11.2f} N.m | {stats_torq['media']:>7.2f} N.m | {stats_torq['desvio_padrao']:>10.2f} N.m")
    print(f"{'Potência':<12} | {stats_pot['min']:>7.2f} W   | {stats_pot['max']:>7.2f} W   | "
          f"{stats_pot['range']:>11.2f} W   | {stats_pot['media']:>7.2f} W   | {stats_pot['desvio_padrao']:>10.2f} W")

    print("\n--- MÉTRICAS DE ERRO (Real/Medido vs. Gêmeo Digital) ---")
    print("-" * 88)
    print(f"{'Variável':<12} | {'MAE (Erro Médio)':<20} | {'RMSE (Picos)':<18} | {'NMAE (Global)':<14} | {'Fundo de escala usado'}")
    print("-" * 88)
    print(f"{'RPM':<12} | {mae_rpm:>7.2f} RPM          | {rmse_rpm:>7.2f} RPM        | "
          f"{nmae_rpm:>6.2f} %       | {np.max(np.abs(rpm_real)):.2f} RPM")
    print(f"{'Torque':<12} | {mae_torq:>7.2f} N.m          | {rmse_torq:>7.2f} N.m        | "
          f"{nmae_torq:>6.2f} %       | {np.max(np.abs(torques_filtrados)):.2f} N.m")
    print(f"{'Potência':<12} | {mae_pot:>7.2f} W            | {rmse_pot:>7.2f} W          | "
          f"{nmae_pot:>6.2f} %       | {np.max(np.abs(potencias_filtradas)):.2f} W")
    print("=" * 88 + "\n")

    # Retorna tudo estruturado, útil para uso programático (ex.: gerar tabela LaTeX)
    return {
        "duracao_ensaio_s": duracao_ensaio,
        "passo_hardware_ms": passo_hardware_estimado * 1000,
        "faixas": {
            "vento": stats_vento,
            "rpm": stats_rpm,
            "torque": stats_torq,
            "potencia": stats_pot,
        },
        "erros": {
            "rpm": {"mae": mae_rpm, "rmse": rmse_rpm, "nmae": nmae_rpm},
            "torque": {"mae": mae_torq, "rmse": rmse_torq, "nmae": nmae_torq},
            "potencia": {"mae": mae_pot, "rmse": rmse_pot, "nmae": nmae_pot},
        },
    }


if __name__ == "__main__":
    perfil = input("Digite o perfil de vento (ex: CONSTANTE, DEGRAU, NATURAL): ").strip()
    calcular_metricas_do_arquivo(f"dados_ensaio_{perfil}.npz")