import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from scipy.signal import butter, filtfilt

# =============================================================================
# ESTILO GLOBAL
# =============================================================================
def configurar_estilo():
    rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "cm",

        "font.size": 10,
        "axes.titlesize": 10,
        "axes.labelsize": 9.5,
        "legend.fontsize": 8,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,

        "lines.linewidth": 1.2,
        "axes.grid": True,
        "grid.linewidth": 0.5,
        "grid.alpha": 0.5,
        "axes.linewidth": 0.8,

        "legend.frameon": True,
        "legend.framealpha": 0.9,
        "legend.edgecolor": "0.8",
        "legend.borderpad": 0.4,
        "legend.handlelength": 1.6,

        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
    })

# Paleta fixa
COR_SENSOR       = "black"    # Dados brutos do sensor
COR_MODELO       = "#7B2D8E"  
COR_REF          = "#1F5FBF"  
COR_ERRO         = "#D62728"  
COR_IDEAL        = "#E7969C"  
COR_POT_MODELO   = "#2E7D32"  
COR_BETZ         = "#D62728"


def _fig_width(largura_relativa=1.0):
    largura_textwidth_cm = 16.5
    return (largura_textwidth_cm * largura_relativa) / 2.54


def _finalizar(fig, nome_arquivo):
    fig.align_ylabels()
    fig.savefig(nome_arquivo, format="pdf")
    plt.close(fig)


def plotar_graficos_do_arquivo(caminho_arquivo="dados_ensaio_CONSTANTE.npz", nome_ensaio="ensaio_offline"):
    configurar_estilo()
    print(f"Carregando dados de: {caminho_arquivo}...")

    try:
        dados = np.load(caminho_arquivo)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        return

    t_hw = dados['tempos_hardware_fisico']
    t_sim = dados['tempos_simulacao_digital']

    if len(t_hw) == 0 or len(t_sim) == 0:
        print("Dados insuficientes no arquivo para gerar gráficos.")
        return

    def interpolar_twin_para_hw(sinal_twin):
        return np.interp(t_hw, t_sim, sinal_twin)

    # Filtro mantido apenas para o Cp (que costuma ter muito ruído/divisão por zero)
    passo_hardware_estimado = np.mean(np.diff(t_hw))
    fs = 1.0 / passo_hardware_estimado
    nyq = 0.5 * fs
    fc = 1.0 / (2 * np.pi * 0.1)
    wn = min(fc / nyq, 0.99)
    b, a = butter(2, wn, btype='low')

    torques_brutos = dados['torques_medidos_sensor_nm']
    potencias_brutas = dados['potencias_medidas_sensor']
    cp_reais = dados['coeficientes_potencia_reais']
    torques_ref = dados['torques_hss_referencia']

    cp_filtrado_plot = filtfilt(b, a, cp_reais)

    torque_twin_interp = interpolar_twin_para_hw(dados['torques_no_eixo_digital'])
    pot_twin_interp = interpolar_twin_para_hw(dados['potencias_gerada'])
    rpm_twin_interp = interpolar_twin_para_hw(dados['velocidades_angulares_gerador_digital'])

    # =========================================================================
    # PLOT 1: Vento, Seguimento de Referência, Erro de Seguimento
    # =========================================================================
    fig1, (ax_v, ax_seg, ax_err_seg) = plt.subplots(
        1, 3, figsize=(_fig_width(1.0), 2.8),
        gridspec_kw={"width_ratios": [1, 1.5, 1]}, constrained_layout=True
    )

    ax_v.plot(t_sim, dados['ventos_simulacao_entrada'], color="#1F5FBF", lw=1.0, label="Vento")
    ax_v.set_ylabel("Velocidade [m/s]")
    ax_v.set_xlabel("Tempo [s]")
    ax_v.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02))

    ax_seg.plot(t_hw, torques_brutos, color=COR_SENSOR, lw=0.9, alpha=0.75, label="Sensor")
    ax_seg.plot(t_hw, torques_ref, color=COR_REF, lw=1.1, label="Referência")
    ax_seg.set_ylabel("Torque [N.m]")
    ax_seg.set_xlabel("Tempo [s]")
    ax_seg.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2)

    erro_seguimento = torques_ref - torques_brutos
    ax_err_seg.plot(t_hw, erro_seguimento, color=COR_ERRO, lw=0.8)
    ax_err_seg.axhline(0, color="black", lw=0.6, ls="--")
    ax_err_seg.set_ylabel("Erro (Ref - Real) [N.m]")
    ax_err_seg.set_xlabel("Tempo [s]")

    _finalizar(fig1, f"{nome_ensaio}_1_vento_seguimento.pdf")

    # =========================================================================
    # PLOT 2: Potência Gêmeo/Real e Erro Modelo Potência
    # =========================================================================
    fig2, (ax_pot, ax_err_pot) = plt.subplots(
        1, 2, figsize=(_fig_width(0.9), 2.8),
        gridspec_kw={"width_ratios": [1.5, 1]}, constrained_layout=True
    )

    ax_pot.plot(t_hw, potencias_brutas, color=COR_SENSOR, lw=0.9, alpha=0.75, label="Sensor")
    ax_pot.plot(t_sim, dados['potencias_gerada'], color=COR_POT_MODELO, lw=1.2, label="Gêmeo")
    ax_pot.set_ylabel("Potência [W]")
    ax_pot.set_xlabel("Tempo [s]")
    ax_pot.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2)

    erro_pot = potencias_brutas - pot_twin_interp
    ax_err_pot.plot(t_hw, erro_pot, color=COR_ERRO, lw=0.8)
    ax_err_pot.axhline(0, color="black", lw=0.6, ls="--")
    ax_err_pot.set_ylabel("Erro Modelo [W]")
    ax_err_pot.set_xlabel("Tempo [s]")

    _finalizar(fig2, f"{nome_ensaio}_2_potencia_modelo.pdf")

    # =========================================================================
    # PLOT 3: Torque Gêmeo/Real e Erro Modelo Torque
    # =========================================================================
    fig3, (ax_torq, ax_err_torq) = plt.subplots(
        1, 2, figsize=(_fig_width(0.9), 2.8),
        gridspec_kw={"width_ratios": [1.5, 1]}, constrained_layout=True
    )

    ax_torq.plot(t_hw, torques_brutos, color=COR_SENSOR, lw=0.9, alpha=0.75, label="Sensor")
    ax_torq.plot(t_sim, dados['torques_no_eixo_digital'], color=COR_MODELO, lw=1.2, label="Gêmeo")
    ax_torq.set_ylabel("Torque [N.m]")
    ax_torq.set_xlabel("Tempo [s]")
    ax_torq.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2)

    erro_torq = torques_brutos - torque_twin_interp
    ax_err_torq.plot(t_hw, erro_torq, color=COR_ERRO, lw=0.8)
    ax_err_torq.axhline(0, color="black", lw=0.6, ls="--")
    ax_err_torq.set_ylabel("Erro Modelo [N.m]")
    ax_err_torq.set_xlabel("Tempo [s]")

    _finalizar(fig3, f"{nome_ensaio}_3_torque_modelo.pdf")

    # =========================================================================
    # PLOT 4: Tensão/FEM, Corrente, Coeficiente de Potência (Cp)
    # =========================================================================
    fig4, (ax_tensao, ax_corrente, ax_cp) = plt.subplots(
        1, 3, figsize=(_fig_width(1.0), 2.8), constrained_layout=True
    )

    ax_tensao.plot(t_sim, dados['tensoes_barramento_volts'], color="#1F5FBF", lw=1.1, label="Capacitor")
    ax_tensao.plot(t_sim, dados['forca_eletromotriz_filtrada'], color="#E8871E", lw=0.9, ls="--", label="FEM")
    ax_tensao.set_ylabel("Tensão [V]")
    ax_tensao.set_xlabel("Tempo [s]")
    ax_tensao.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2)

    ax_corrente.plot(t_sim, dados['correntes_armadura_digitais'], color=COR_ERRO, lw=1.1, label="Armadura")
    ax_corrente.set_ylabel("Corrente [A]")
    ax_corrente.set_xlabel("Tempo [s]")
    ax_corrente.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02))

    ax_cp.plot(t_hw, cp_filtrado_plot, color="black", lw=1.0, ls="--", alpha=0.75, label="Real")
    ax_cp.plot(t_sim, dados['coeficientes_potencia_digitais'], color=COR_MODELO, lw=1.1, label="Gêmeo")
    ax_cp.axhline(0.593, color=COR_BETZ, lw=0.9, ls="--", label="Betz")
    ax_cp.set_ylim(0, 0.7)
    ax_cp.set_ylabel(r"$C_p$ [-]")
    ax_cp.set_xlabel("Tempo [s]")
    ax_cp.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3)

    _finalizar(fig4, f"{nome_ensaio}_4_eletrica_cp.pdf")

    # =========================================================================
    # PLOT 5: Rotação (RPM) Gêmeo/Real/Ideal e Erro de RPM
    # =========================================================================
    fig5, (ax_rpm, ax_err_rpm) = plt.subplots(
        1, 2, figsize=(_fig_width(0.9), 2.8),
        gridspec_kw={"width_ratios": [1.5, 1]}, constrained_layout=True
    )

    ax_rpm.plot(t_hw, dados['velocidades_angulares_reais_rpm'], color=COR_SENSOR, lw=0.9, alpha=0.75, label="Sensor")
    ax_rpm.plot(t_sim, dados['velocidades_angulares_gerador_digital'], color=COR_MODELO, lw=1.2, label="Gêmeo")
    ax_rpm.plot(t_hw, dados['velocidades_angulares_ideais_rpm'], color=COR_IDEAL, lw=1.1, ls="--", label="Ideal")
    ax_rpm.set_ylabel("Rotação [RPM]")
    ax_rpm.set_xlabel("Tempo [s]")
    ax_rpm.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3)

    erro_rpm = dados['velocidades_angulares_reais_rpm'] - rpm_twin_interp
    ax_err_rpm.plot(t_hw, erro_rpm, color=COR_ERRO, lw=0.8)
    ax_err_rpm.axhline(0, color="black", lw=0.6, ls="--")
    ax_err_rpm.set_ylabel("Erro Modelo [RPM]")
    ax_err_rpm.set_xlabel("Tempo [s]")

    _finalizar(fig5, f"{nome_ensaio}_5_rpm_modelo.pdf")

    print("Gráficos gerados com sucesso!")

if __name__ == "__main__":
    perfil = input("Digite o perfil de vento (ex: CONSTANTE, DEGRAU, NATURAL): ").strip()
    plotar_graficos_do_arquivo(f"dados_ensaio_{perfil}.npz", nome_ensaio=f"ensaio_offline_{perfil}")