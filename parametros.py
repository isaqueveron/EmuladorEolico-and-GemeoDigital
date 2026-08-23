import numpy as np

# ==================================================================================
# PARÂMETROS ELETROMECÂNICOS ATUALIZADOS (NÃO MUDAR - IDENTIFICADOS EM BANCADA/PLACA)
# ==================================================================================
CONSTANTE_VELOCIDADE_GERADOR_V_RAD_S = 2.675717 
OFFSET_FEM = 9.5104 
TORQUE_MAXIMO_MOTOR_NM = 79.63 
COEFICIENTE_ATRITO_GERADOR = 0.001885
# curva real do inversor fisico
pontos_v_inversor_hibrido = np.array([90, 110, 130, 150, 170, 190, 210, 230, 250, 270, 290, 310])
pontos_i_inversor_hibrido = np.array([0.001, 1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5, 12.0, 13.5, 15.0, 16.5])/2
TSR_IDEAL = 7.5
TAXA_VARIACAO_RPM_MAX = 100

# ==================================================================================

# chutes
RPM = [0, 500, 550, 600, 700, 900, 1000]
GANHOS = [1/25, 1/25, 1/18, 1/15, 1/1.5, 1/1, 1/0.5]
TABELA_GANHO_ARMADURA = dict(zip(RPM, GANHOS))
GANHO_ARMADURA = GANHOS[0]
TAU_ARMADURA = 0.03
CAPACITANCIA_BARRAMENTO_FARADAY = 0.007
INERCIA_GERADOR_KG_M2 = 2 * COEFICIENTE_ATRITO_GERADOR # 2 como tau mecanico se mostrou melhor que o ensaiado...
# curva otima ajustada pelo main_gemeo_pid
# pontos_v_inversor_hibrido = np.array([30.02, 57.23, 84.44, 111.64, 138.85, 166.06, 193.27, 220.48, 247.69, 274.9, 302.11, 329.32])
# pontos_i_inversor_hibrido = np.array([0.17, 0.68, 2.96, 4.19, 4.31, 4.69, 5.78, 7.41, 9.37, 11.36, 13.38, 15.36])

pontos_r_inversor_hibrido = pontos_v_inversor_hibrido/pontos_i_inversor_hibrido
# =============================================================================

# apenas para isolar o comportamento do motor/gerador de bancada,
COEFICIENTE_ATRITO_TURBINA = 0.0
INERCIA_TURBINA_KG_M2 = 0.0

DENSIDADE_AR_KG_M3 = 1.2754
RAIO_TURBINA_METROS = 2.5 # escolha
RELACAO_TRANSMISSAO_CAIXA_ENGRENAGENS = 4 # escolhaw
VELOCIDADE_MAXIMA_PAS_GRAUS_S = 5.0 # escolha
TENSAO_MAXIMA_INVERSOR_V = pontos_v_inversor_hibrido[-1] # tabela inversor hibrido
TENSAO_MINIMA_INVERSOR_V = pontos_v_inversor_hibrido[0]  # tabela inversor hibrido
TEMPO_ESPERA_LIGAR = 5.0  # Tempo necessário (em segundos) com tensão alta para ligar
POTENCIA_MECANICA_MAXIMA_W = 3000 # escolha

PASSO_SIMULACAO_SEGUNDOS = 0.004 
PASSO_HARDWARE_SEGUNDOS = 0.01 # deve ser maior que a latencia da comunicacao
TEMPO_TOTAL_EMULACAO_SEGUNDOS = 100 # escolha

TAXA_ATUALIZACAO_GRAFICOS_SEGUNDOS = 1.0 #escolha

CONSTANTE_TEMPO_FILTRO_SENSOR_TORQUE = 0.1
FREQUENCIA_CORTE_FILTRO_COMANDO_VELOCIDADE = 20
CONSTANTE_TEMPO_FILTRO_VELOCIDADE_ALVO = 0.5
CONSTANTE_TEMPO_FILTRO_FORCAELETROMOTRIZ = 0.0

#PERFIL_VENTO = 'CONSTANTE'
#PERFIL_VENTO = 'ESCADA' 
PERFIL_VENTO = 'NATURAL'
#PERFIL_VENTO = 'RAMPA'
from numpy import load
VETOR_VENTO_M_S = load('vetor_vento.npy')
vento_constante = 5

