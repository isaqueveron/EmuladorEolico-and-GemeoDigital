import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

from parametros import *
from modelo_aerogerador import TurbinaVirtual

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
NOME_FIGURA = f"otimizador_cinematica_potencia_{PERFIL_VENTO}.pdf"
SALVAR_NPZ = True          # salva sim_original.npz / sim_otimizada.npz (para reutilizar nos plots)
MOSTRAR_FIGURA = True

# Tabelas V x I (ambas vêm do parametros.py)
TABELAS = {
    "original":  (pontos_v_inversor_hibrido,     pontos_i_inversor_hibrido),
    "otimizada": (pontos_v_inversor_hibrido_opt, pontos_i_inversor_hibrido_opt),
}


def calcular_resistencias(v, i):
    """R = V/I em cada nó da tabela. Onde I = 0 usa 1e50 (circuito aberto), evitando inf/NaN na interpolação.
    (As resistências são calculadas aqui; as variáveis pontos_r_* do parametros.py não são usadas.)"""
    v = np.asarray(v, dtype=float)
    i = np.asarray(i, dtype=float)
    r = np.full_like(v, 1e50)
    ok = i > 1e-9
    r[ok] = v[ok] / i[ok]
    return r


class RegistroDeSimulacao:
    def __init__(self, duracao_s, passo_simulacao):
        self.n_sim = int(duracao_s / passo_simulacao) + 1
        self.idx_sim = 0
        n = self.n_sim
        self.tempos_simulacao_digital = np.zeros(n)
        self.ventos_simulacao_entrada = np.zeros(n)
        self.velocidades_angulares_gerador_digital = np.zeros(n)
        self.velocidades_angulares_gerador_ideais = np.zeros(n)
        self.tensoes_barramento_volts = np.zeros(n)
        self.correntes_armadura = np.zeros(n)
        self.potencias_gerada = np.zeros(n)
        self.potencia_eletrica_entregue_w = np.zeros(n)
        self.potencias_perdas_efeito_joule = np.zeros(n)


def calcular_velocidade_vento_degraus(t):
    if t < 10.0: return 0.0
    if t < 20.0: return 1.0
    if t < 30.0: return 2.0
    if t < 40.0: return 3.0
    if t < 50.0: return 4.0
    if t < 60.0: return 5.0
    if t < 70.0: return 6.0
    if t < 80.0: return 7.0
    return 0.0


def calcular_velocidade_vento_rampa(t):
    if 0.0 <= t < 50.0:
        return (10.0 / 50.0) * t
    elif 50.0 <= t < 100.0:
        return 10.0 - ((10.0 / 50.0) * (t - 50.0))
    return 0.0


def simular(nome, v_tab, i_tab):
    """Simula o Gêmeo Digital em malha aberta com a tabela V x I informada."""
    v_tab = np.asarray(v_tab, dtype=float)
    i_tab = np.asarray(i_tab, dtype=float)
    r_tab = calcular_resistencias(v_tab, i_tab)
    v_min_conexao = v_tab[0]     # o inversor conecta quando a FEM passa do 1º ponto da PRÓPRIA tabela

    turbina = TurbinaVirtual(
        constante_velocidade=CONSTANTE_VELOCIDADE_GERADOR_V_RAD_S,
        offset_fem=OFFSET_FEM,
        tabela_ganho_armadura=TABELA_GANHO_ARMADURA,
        tau_armadura=TAU_ARMADURA,
        capacitancia_barramento=CAPACITANCIA_BARRAMENTO_FARADAY,
        raio_turbina=RAIO_TURBINA_METROS,
        inercia_turbina=INERCIA_TURBINA_KG_M2,
        inercia_gerador=INERCIA_GERADOR_KG_M2,
        coeficiente_atrito_turbina=COEFICIENTE_ATRITO_TURBINA,
        coeficiente_atrito_gerador=COEFICIENTE_ATRITO_GERADOR,
        taxa_variacao_rpm_maxima=TAXA_VARIACAO_RPM_MAX,
        velocidade_angular_maxima_pitch=VELOCIDADE_MAXIMA_PAS_GRAUS_S,
        torque_maximo_motor=TORQUE_MAXIMO_MOTOR_NM,
        tsr_ideal=TSR_IDEAL,
        relacao_transmissao_caixa_engrenagens=RELACAO_TRANSMISSAO_CAIXA_ENGRENAGENS,
        modelo_coeficiente_potencia='classico',
        densidade_ar_kg_m3=DENSIDADE_AR_KG_M3,
        sinal_controle_mppt='resistencia de carga'
    )
    reg = RegistroDeSimulacao(TEMPO_TOTAL_EMULACAO_SEGUNDOS, PASSO_SIMULACAO_SEGUNDOS)

    print(f"\n[{nome}] Simulando {TEMPO_TOTAL_EMULACAO_SEGUNDOS}s | conexão do inversor com FEM >= {v_min_conexao:.2f} V")
    tempo = 0.0
    idx_vento = 0
    acumulado = 0.0
    conectado = False
    vento = 0.0

    while tempo < TEMPO_TOTAL_EMULACAO_SEGUNDOS:
        if tempo >= PASSO_SIMULACAO_SEGUNDOS:
            if PERFIL_VENTO == 'CONSTANTE':
                vento = vento_constante * (tempo / 10.0) if tempo < 10.0 else vento_constante
            elif PERFIL_VENTO == 'ESCADA':
                vento = calcular_velocidade_vento_degraus(tempo)
            elif PERFIL_VENTO == 'RAMPA':
                vento = calcular_velocidade_vento_rampa(tempo)
            elif PERFIL_VENTO == 'NATURAL':
                vento = VETOR_VENTO_M_S[min(idx_vento, len(VETOR_VENTO_M_S) - 1)]
                idx_vento += 1

            # --- MPPT do inversor (impedância emulada pela tabela V x I) ---
            fem = turbina.get_forca_eletromotriz()
            if fem >= v_min_conexao:
                acumulado += PASSO_SIMULACAO_SEGUNDOS
                if acumulado >= TEMPO_ESPERA_LIGAR:
                    if not conectado:
                        print(f"  [{tempo:.2f}s] Inversor ligou")
                    conectado = True
            else:
                if conectado:
                    print(f"  [{tempo:.2f}s] Inversor desligou")
                acumulado = 0.0
                conectado = False

            if conectado:
                r_carga = np.interp(turbina.get_tensao_capacitor_volts(), v_tab, r_tab, left=1e50)
            else:
                r_carga = 1e50
            turbina.set_flag_vazio(not conectado)

            turbina.executar_passo_simulacao(vento, 0, PASSO_SIMULACAO_SEGUNDOS, r_carga)

            if reg.idx_sim < reg.n_sim:
                k = reg.idx_sim
                reg.tempos_simulacao_digital[k] = tempo
                reg.ventos_simulacao_entrada[k] = vento
                reg.velocidades_angulares_gerador_digital[k] = turbina.get_velocidade_angular_gerador_rad_s() * 60.0 / (2.0 * np.pi)
                reg.velocidades_angulares_gerador_ideais[k] = (vento * TSR_IDEAL / RAIO_TURBINA_METROS) * RELACAO_TRANSMISSAO_CAIXA_ENGRENAGENS * 60.0 / (2.0 * np.pi)
                reg.tensoes_barramento_volts[k] = turbina.get_tensao_capacitor_volts()
                reg.correntes_armadura[k] = turbina.get_corrente_armadura_amperes()
                reg.potencias_gerada[k] = turbina.get_potencia_gerada_w()
                reg.potencia_eletrica_entregue_w[k] = turbina.get_potencia_eletrica_entregue_w()
                reg.potencias_perdas_efeito_joule[k] = turbina.get_potencia_perdas_efeito_joule_w()
                reg.idx_sim += 1

        tempo += PASSO_SIMULACAO_SEGUNDOS

    return reg


def energia_wh(potencias_w, n):
    return np.sum(potencias_w[:n]) * PASSO_SIMULACAO_SEGUNDOS / 3600.0


def salvar_npz(reg, arquivo):
    s = reg.idx_sim
    np.savez_compressed(arquivo, **{k: v[:s] for k, v in vars(reg).items() if isinstance(v, np.ndarray)})


# =============================================================================
# FIGURA NO PADRÃO DO ARTIGO (gerar_plots.py)
# =============================================================================
def configurar_estilo():
    rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "cm",
        "font.size": 10, "axes.titlesize": 10, "axes.labelsize": 9.5,
        "legend.fontsize": 8, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "lines.linewidth": 1.2,
        "axes.grid": True, "grid.linewidth": 0.5, "grid.alpha": 0.5, "axes.linewidth": 0.8,
        "legend.frameon": True, "legend.framealpha": 0.9, "legend.edgecolor": "0.8",
        "legend.borderpad": 0.4, "legend.handlelength": 1.6,
        "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
    })


COR_ORIGINAL = "#1F5FBF"
COR_OTIMIZADA = "#2E7D32"
COR_IDEAL = "#E7969C"


def _fig_width(largura_relativa=1.0):
    return (16.5 * largura_relativa) / 2.54


def _v(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


def plotar_comparativo(reg_o, reg_p, e_o, e_p, nome_arquivo):
    configurar_estilo()
    n = min(reg_o.idx_sim, reg_p.idx_sim)
    t = reg_o.tempos_simulacao_digital[:n]
    ideal = reg_o.velocidades_angulares_gerador_ideais[:n]
    rpm_o = reg_o.velocidades_angulares_gerador_digital[:n]
    rpm_p = reg_p.velocidades_angulares_gerador_digital[:n]
    pot_o = reg_o.potencias_gerada[:n]
    pot_p = reg_p.potencias_gerada[:n]

    fig, (ax_rpm, ax_pot) = plt.subplots(
        1, 2, figsize=(_fig_width(1.0), 2.8),
        gridspec_kw={"width_ratios": [1,1]}, constrained_layout=True
    )

    # (1) Cinemática
    ax_rpm.plot(t, rpm_o, color=COR_ORIGINAL, lw=1.1, label="Original")
    ax_rpm.plot(t, rpm_p, color=COR_OTIMIZADA, lw=1.1, label="Otimizada")
    ax_rpm.plot(t, ideal, color=COR_IDEAL, lw=1.1, ls="--", label="Ideal")
    ax_rpm.set_ylabel("Rotação [RPM]")
    ax_rpm.set_xlabel("Tempo [s]")
    ax_rpm.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3,
                  fontsize=7.5, columnspacing=0.8, handlelength=1.2)

    """# (2) Erro de rastreio
    ax_err.plot(t, rpm_o - ideal, color=COR_ORIGINAL, lw=0.9)
    ax_err.plot(t, rpm_p - ideal, color=COR_OTIMIZADA, lw=0.9)
    ax_err.axhline(0, color="black", lw=0.6, ls="--")
    ax_err.set_ylabel("Erro de rastreio [RPM]")
    ax_err.set_xlabel("Tempo [s]")"""

    # (3) Potência gerada
    ax_pot.plot(t, pot_o, color=COR_ORIGINAL, lw=1.1, label=f"Original ({_v(e_o)} Wh)")
    ax_pot.plot(t, pot_p, color=COR_OTIMIZADA, lw=1.1, label=f"Otimizada ({_v(e_p)} Wh)")
    ax_pot.fill_between(t, pot_o, pot_p, color=COR_OTIMIZADA, alpha=0.15, lw=0)
    ax_pot.set_ylabel("Potência gerada [W]")
    ax_pot.set_xlabel("Tempo [s]")
    ax_pot.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2,
                  fontsize=7.5, columnspacing=0.8, handlelength=1.2)

    fig.align_ylabels()
    fig.savefig(nome_arquivo, format="pdf")
    plt.close(fig)


if __name__ == "__main__":
    regs = {nome: simular(nome, v, i) for nome, (v, i) in TABELAS.items()}
    ro, rp = regs["original"], regs["otimizada"]

    # Energia GERADA (potência eletromagnética Te·w) e, só como informação, energia ENTREGUE (V·ia)
    eg_o, eg_p = energia_wh(ro.potencias_gerada, ro.idx_sim), energia_wh(rp.potencias_gerada, rp.idx_sim)
    ee_o, ee_p = energia_wh(ro.potencia_eletrica_entregue_w, ro.idx_sim), energia_wh(rp.potencia_eletrica_entregue_w, rp.idx_sim)
    ej_o, ej_p = energia_wh(ro.potencias_perdas_efeito_joule, ro.idx_sim), energia_wh(rp.potencias_perdas_efeito_joule, rp.idx_sim)

    print("\n" + "=" * 78)
    print(f"[ENERGIA GERADA]   original: {eg_o:.4f} Wh | otimizada: {eg_p:.4f} Wh | ganho: {100 * (eg_p / eg_o - 1):+.1f}%")
    print(f"[info] entregue (V·ia): original {ee_o:.3f} Wh | otimizada {ee_p:.3f} Wh | variação {100 * (ee_p / ee_o - 1):+.1f}%")
    print(f"[info] perdas Joule   : original {ej_o:.3f} Wh | otimizada {ej_p:.3f} Wh")

    n = min(ro.idx_sim, rp.idx_sim)
    ideal = ro.velocidades_angulares_gerador_ideais[:n]
    mk = ideal > 0.3 * ideal.max()
    for nome, reg in (("original", ro), ("otimizada", rp)):
        err = reg.velocidades_angulares_gerador_digital[:n] - ideal
        print(f"[rastreio] {nome:9s}: erro médio {err[mk].mean():+6.1f} RPM | erro absoluto médio {np.abs(err[mk]).mean():5.1f} RPM "
              f"({100 * np.abs(err[mk]).mean() / ideal.max():.1f}% do pico ideal)")
    print("=" * 78)

    plotar_comparativo(ro, rp, eg_o, eg_p, NOME_FIGURA)
    print(f"Figura salva em: {NOME_FIGURA}")
    if SALVAR_NPZ:
        salvar_npz(ro, "sim_original.npz")
        salvar_npz(rp, "sim_otimizada.npz")
        print("Dados salvos: sim_original.npz, sim_otimizada.npz")
    if MOSTRAR_FIGURA:
        plt.show()