from typing import Literal
import numpy as np
from numpy.testing.print_coercion_tables import print_new_cast_table
from scipy.stats import uniform, triang, lognorm, expon, gamma, fisk, norm,truncexpon
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


Maint   = Literal["R", "S", None]
Chemistry = Literal["VRFB", "AORFB"]

c_assembling = 50
c_testing = 50
c_handling = 12
c_pumps = 82
c_pipes = 127.4
c_PCS = 10
c_HVAC = 34
c_case = 84.3
c_shelf = 142
c_bolts = 53.4

n_e_minus = 1
DoD_max = 0.6
F = 96485.33

C_fabr_sol= 0.8
C_tank_vol = 0.295

c_frame = 33
c_EP = 180
c_IP = 55.2
c_CC = 151
P_b_nom = 1000
f_d = 0.2
d_r = 0.08
N_y = 20
r_d_y = 0.12
n_rep_P = 1
t_rep_P = 10

OM_power_fixed = 12
OM_energy_fixed = 1
cyc_day=1
cap_lim=0.8


DOD_max=0.6
r_i_y=0.01
c_el=0.125
O_cost=8.4
om=3

MW_active_anode = 0.110
MW_active_Catholyte = 0.452
c_SE_anode = 0.041
c_SE_Catholyte = 0.02
c_active_anode = 0.43
c_active_Catholyte = 1.39
rho_el_anode = 1.61
rho_el_catholyte = 1.913
conc_act_catholyte = 2.0
conc_act_anode = 5.0
eta_sys_d = 0.968
ASR = 2.04
N=50



c_m = 12
c_BP = 42
c_felt = 13
OCV = 1.77
r_CO = 0.000018
i_d = 50.0


r_time = 0.00086
r_ED = 0.00002
eta_rt=0.81


def bop_cost(c_pumps, c_pipes, c_PCS, c_HVAC, c_case, c_shelf, c_bolts):
    C_BOP = c_pumps + c_pipes + c_PCS + c_HVAC + c_case + c_shelf + c_bolts
    # print("BOP Cost: ", C_BOP)
    return C_BOP


def additional_cost(c_assembling, c_testing, c_handling):
    C_add = c_assembling + c_testing + c_handling
    # print("Additional Cost: ", C_add)
    return C_add


def electrolyte_energy_cost(rho_el_anode,rho_el_catholyte, MW_active_anode,MW_active_Catholyte,conc_act_anode, conc_act_catholyte, n_e_minus, DoD_max, F, c_active_anode,
                            c_active_Catholyte,c_SE_anode,c_SE_Catholyte, OCV, i_d, ASR, eta_sys_d, C_fabr_sol, C_tank_vol, c_m, c_BP, c_felt, c_frame, c_EP, c_IP,
        c_CC, N, ) -> float:
    # 1. 公式 11：S_ratio
    # S_ratio = conc_act * MW_active / (rho_el - conc_act * MW_active)
    S_ratio_anode = conc_act_anode * MW_active_anode / (rho_el_anode - conc_act_anode * MW_active_anode)
    S_ratio_Catholyte = conc_act_catholyte * MW_active_Catholyte / (rho_el_catholyte - conc_act_catholyte * MW_active_Catholyte)

    # 2. 公式 10：C_el_weight
    # C_el_weight = c_active + (c_SE / S_ratio)
    C_el_weight_anode = c_active_anode + (c_SE_anode / S_ratio_anode)
    C_el_weight_Catholyte = c_active_Catholyte + (c_SE_Catholyte / S_ratio_Catholyte)

    # 3. 公式 9：C_e_tr
    # C_e_tr = (MW_active * C_el_weight) / (DoD_max * n_e_minus)
    C_e_tr_anode = (MW_active_anode * C_el_weight_anode) / (DoD_max * n_e_minus)
    C_e_tr_Catholyte = (MW_active_Catholyte * C_el_weight_Catholyte) / (DoD_max * n_e_minus)

    # 5. 公式 7：V_cell_d
    V_cell_d =  OCV - i_d * ASR * 1e-3

    # 6. 公式 6：V_eff_sys
    V_eff_sys = V_cell_d * eta_sys_d

    # 9. 公式 3：C_electrolyte_m
    C_electrolyte_m = ((C_e_tr_anode + C_e_tr_Catholyte) / (F * V_eff_sys)) * 3600 * 1000

    # 4 公式 4. rho_E
    rho_E = conc_act_catholyte * F * V_eff_sys * DoD_max * n_e_minus / 3600 / 1000
    C_electrolyte_f = C_fabr_sol / rho_E
    C_tank = C_tank_vol / rho_E

    # 10. 公式 2：C_E
    C_E = C_electrolyte_m + C_electrolyte_f + C_tank


    # 公式 16：a_active
    a_active = 1 * 1000 / ((i_d * 10000 / 1000) * V_eff_sys)
    # 公式 17：sum_term
    sum_term = (
            c_m
            + c_BP * ((N + 1) / N)
            + 2 * (c_felt + c_frame)
            + (2 * c_EP + c_IP + 2 * c_CC) * (1 / N)
    )

    # 公式 15：sum_term
    C_reactor = a_active * sum_term
    C_add = additional_cost(c_assembling = c_assembling, c_testing = c_testing, c_handling = c_handling)
    C_BOP = bop_cost(c_pumps = c_pumps, c_pipes = c_pipes, c_PCS = c_PCS, c_HVAC = c_HVAC, c_case = c_case, c_shelf = c_shelf, c_bolts = c_bolts)
    C_P = C_reactor + C_BOP + C_add
    # print("Electrolyte materials Cost: ", C_electrolyte_m)
    # print("Electrolyte fabrication Cost: ", C_electrolyte_f)
    # print("BOP Cost: ", C_BOP)
    # print("Electrolyte C_tank Cost: ", C_tank)
    # print("Cost of membrane:",c_m*a_active)
    # print("Cost of bipolar plate:",c_BP * ((N + 1) / N)*a_active)
    # print("Cost of c_felt:",2*c_felt*a_active)
    # print("Cost of c_frame:",2*c_frame*a_active)
    # print("Cost of c_EP:",2*c_EP*(1/N)*a_active)
    # print("Cost of c_CC:",2*c_CC*(1/N)*a_active)
    # print("Cost of c_IP:", c_IP * (1/N) * a_active)
    # print("reactor cost: ", C_reactor)
    # print("Add cost: ", C_add)
    # print("energy-related Cost:",C_E)
    # print("power-related Cost:", C_P)

    return  C_E, C_P, a_active

def calculate_system_cost(C_E, C_P, E_b_nom, P_b_nom):
    C_b = C_E * E_b_nom + C_P * P_b_nom
    # print("Capital Cost", C_b/E_b_nom)
    return C_b


def financing_model(C_b, f_d, d_r, N_y, r_d_y):

    # Eq. (24): Capital Recovery Factor
    CRF = (d_r * (1 + d_r) ** N_y) / ((1 + d_r) ** N_y - 1)

    # Eq. (22): Initial investment (equity-financed part)
    I0 = C_b * (1 - f_d)

    # Eq. (23): Annual loan payment (debt-financed part)
    Lt = C_b * f_d * CRF
    Lt_list = []
    for year in range(1,N_y+1):
        Lt_d_y = Lt / ((1+r_d_y) ** year)
        Lt_list.append(Lt_d_y)

    return  I0,  Lt_list



def lcos_replacement_cost(P_b_nom, n_rep_P, r_d_y, t_rep_P, C_m, C_felt, a_active) -> float:
    C_rep_P = (C_m + 2 * C_felt) * a_active
    df_P = sum(1 / (1 + r_d_y) ** (k * t_rep_P) for k in range(1, n_rep_P + 1))
    C_rep_t = C_rep_P * P_b_nom * df_P
    return C_rep_t





def calculate_discharged_energy_cost(E_b_nom, Pb_nom, OM_power_fixed,OM_energy_fixed, cyc_day, cap_lim, r_CO,
                                     r_ED, r_time, N_y, DOD_max, r_i_y, r_d_y, eta_rt,
                                     c_el, O_cost, om):
    days_per_year = 365
    total_days = N_y * days_per_year  # --- 1. 预计算常数 --- 7300
    N_cyc_day = DOD_max * cyc_day

    # --- 2. 初始化状态变量和参数 ---
    n_cyc_R = 0.0  # n_cyc,t^R (可逆循环计数)
    n_cyc_S = 0.0  # n_cyc,t^S (不可逆循环计数)
    n_time = 0  # n_time,t (时间计数)
    r_i_d = (1 + r_i_y) ** (1 / days_per_year) - 1  # 日通货膨胀率
    r_d_d = (1 + r_d_y) ** (1 / days_per_year) - 1  # 日折现率
    C_ch_om_list = []
    C_v_om_list = []
    C_f_om_list = []
    E_dis_t_list = []
    E_dis_all_list = []
    R, S = 0, 0

    servicing_cost = O_cost * E_b_nom

    # --- 3. 每日模拟循环 ---
    for day_t in range(1, total_days + 1):
        # A. 计算当天的容量 (基于前一天的状态)
        cap_max = 1.0 - r_ED * n_cyc_S - r_time * n_time
        f_cap_t = cap_max - r_CO * n_cyc_R

        # 初始化容量因子和可变运维成本
        CF_t = 1.0

        # --- B. 维护事件检查和执行 (优先级: Servicing > Rebalancing) ---

        # 1. Servicing (reservice): 消除不可逆衰减 (cap_max)
        if cap_max <= cap_lim:
            # 1a. 计算 C_v_om 成本 (Servicing 成本)
            C_v_om = servicing_cost / ((1 + r_d_d) ** day_t)
            C_v_om_list.append(C_v_om)

            # 1b. Servicing 重置 n_cyc^S 和 n_time
            n_cyc_S = 0.0
            n_time = 0
            S += 1

            # 1c. 容量更新 (cap_max 恢复到 1.0)
            cap_max = 1.0
            f_cap_t = cap_max - r_CO * n_cyc_R  # f_cap_t 基于新的 cap_max 重新计算
            CF_t = 1.5

        # 2. Rebalancing (rebalance): 消除可逆衰减 (f_cap_t)
        # 注意：这里必须是 IF，因为 Servicing 恢复后可能仍需 Rebalancing
        if f_cap_t <= cap_lim:
            # 2a. 容量因子增加 (成本增加)
            CF_t = 1.5

            # 2b. Rebalancing 重置 n_cyc^R
            n_cyc_R = 0.0

            R += 1

            # 2c. 容量更新 (f_cap_t 恢复到 cap_max)
            f_cap_t = cap_max

        # --- C. 每日能量和 C_ch 成本计算 (只计算一次) ---

        # 1. E_dis,t (使用维护后或正常衰减的 f_cap,t)
        E_dis_t = E_b_nom * cyc_day * f_cap_t
        E_dis_all_list.append(E_dis_t)
        E_dis_t_d_d = E_dis_t / ((1 + r_d_d) ** day_t)
        E_dis_t_list.append(E_dis_t_d_d)

        # 2. C_OM_energy_lost (C_ch) (使用最新的 CF_t)
        C_OM_energy_lost = c_el * E_dis_t * (CF_t / eta_rt - 1) * (1 + r_i_d) ** (day_t - 2)
        C_OM_energy_lost_d_d = C_OM_energy_lost / ((1 + r_d_d) ** day_t)
        C_ch_om_list.append(C_OM_energy_lost_d_d)

        # --- D. 累加循环计数和时间 (无条件累加) ---
        # 即使发生维护，当天仍然运行一个周期，计数在维护重置后应从 N_cyc_day/1 开始
        n_cyc_R += N_cyc_day
        n_cyc_S += N_cyc_day
        n_time += 1

    # --- 4. 固定运维成本 (每年折现) ---
    for year in range(1, N_y + 1):
        # C_OM_fixed = OM_power_fixed * Pb_nom + OM_energy_fixed*E_b_nom
        C_OM_fixed = 13 * Pb_nom
        # 固定运维成本按年折现 (r_d_y)
        C_OM_fixed_d = C_OM_fixed / ((1 + r_d_y) ** year)
        C_f_om_list.append(C_OM_fixed_d)

    # print(R,S)

    return C_f_om_list, C_v_om_list, C_ch_om_list, E_dis_t_list,E_dis_all_list



def levelized_cost(I_0,Lt_list,C_rep_t,C_f_om_list,C_v_om_list,C_ch_om_list,E_dis_t_list,E_dis_all_list,r_i_y=r_i_y,c_el=c_el):

    r_i_d = (1 + r_i_y) ** (1 / 365 ) - 1  # 日通货膨胀率

    LCOS_net = (I_0 + sum(Lt_list) + C_rep_t + sum(C_f_om_list) + sum(C_v_om_list) + sum(C_ch_om_list)) / sum(E_dis_t_list)
    C_OM_energy_d_i_list = []

    for day_t in range(1,len(E_dis_t_list)):
        C_OM_energy_d_i = E_dis_t_list[day_t] * ((1 + r_i_d) ** (day_t-2))
        C_OM_energy_d_i_list.append(C_OM_energy_d_i)

    plus = sum(C_OM_energy_d_i_list) / sum(E_dis_t_list)


    LCOS = LCOS_net + c_el*plus
    #
    # print("initial Cost:", I_0)
    # print("Load Cost:", sum(Lt_list))
    # print("Replacement Cost:", C_rep_t)
    # print("Operation and Management:", (sum(C_f_om_list) + sum(C_v_om_list) + sum(C_ch_om_list))+C_rep_t)
    # print("Electricity Cost:", c_el * sum(C_OM_energy_d_i_list))
    # print("discharge all energy(kwh):", sum(E_dis_all_list))

    return LCOS_net, LCOS

E_b_nom = 8000

C_E, C_P, a_active = electrolyte_energy_cost(rho_el_anode = rho_el_anode,rho_el_catholyte = rho_el_catholyte
                                             , MW_active_anode = MW_active_anode,MW_active_Catholyte = MW_active_Catholyte, conc_act_anode = conc_act_anode,
                                             conc_act_catholyte = conc_act_catholyte, n_e_minus=n_e_minus, DoD_max=DoD_max, F=F, c_active_anode = c_active_anode ,c_active_Catholyte = c_active_Catholyte,
                        c_SE_anode = c_SE_anode, c_SE_Catholyte = c_SE_Catholyte, OCV=OCV, i_d=i_d, ASR=ASR, eta_sys_d=eta_sys_d,
                                             C_fabr_sol=C_fabr_sol, C_tank_vol=C_tank_vol, c_m=c_m, c_BP=c_BP,
                                             c_felt=c_felt,
                                             c_frame=c_frame, c_EP=c_EP, c_IP=c_IP, c_CC=c_CC, N=N)

C_b = calculate_system_cost(C_E, C_P, E_b_nom=E_b_nom, P_b_nom=P_b_nom)
I0, Lt_list = financing_model(C_b=C_b, f_d=f_d, d_r=d_r, N_y=N_y, r_d_y=r_d_y)
C_rep_t = lcos_replacement_cost(P_b_nom=P_b_nom, n_rep_P=n_rep_P, r_d_y=r_d_y, t_rep_P=t_rep_P, C_m=c_m,
                                C_felt=c_felt, a_active=a_active)
C_f_om_list, C_v_om_list, C_ch_om_list, E_dis_t_list, E_dis_all_list = calculate_discharged_energy_cost(
    E_b_nom=E_b_nom, Pb_nom = P_b_nom, OM_power_fixed = OM_power_fixed,OM_energy_fixed = OM_energy_fixed, cyc_day=cyc_day, cap_lim=cap_lim, r_CO=r_CO,
                             r_ED=r_ED, r_time=r_time, N_y=N_y, DOD_max=DOD_max, r_i_y=r_i_y, r_d_y=r_d_y, eta_rt=eta_rt,
                             c_el=c_el, O_cost=O_cost, om=om)

LCOS_net, LCOS = levelized_cost(I_0=I0, Lt_list=Lt_list, C_rep_t=C_rep_t,
                                      C_f_om_list=C_f_om_list,
                                      C_v_om_list=C_v_om_list, C_ch_om_list=C_ch_om_list,
                                      E_dis_t_list=E_dis_t_list,E_dis_all_list=E_dis_all_list)

# print(sum(E_dis_all_list))
# print("capital Cost:",C_b / E_b_nom)
# print("net LCOS cost:",LCOS_net *1000)
# print("LCOS cost:",LCOS *1000)




def Parameter_sensitive_simulation(E_b_nom, num_iterations):
    variable_parameters = []
    energy_related_results = []
    power_related_results = []
    Capital_results = []
    LCOS_results = []
    LCOS_net_results = []
    for eta_rt in np.linspace(0.6, 1, num_iterations):
    # for r_time in np.logspace(np.log10(1e-6), np.log10(1e-2), num_iterations):
        # c_m = params.get('c_m')
        # c_felt = params.get('c_felt')
        # c_BP = params.get('c_BP')
        # i_d = params.get('i_d')
        # OCV = params.get('OCV')
        # r_ED = params.get('r_ED')  r_CO
        # r_time = params.get('r_time')
        C_E, C_P, a_active = electrolyte_energy_cost(rho_el_anode=rho_el_anode, rho_el_catholyte=rho_el_catholyte
                                                 , MW_active_anode=MW_active_anode,
                                                 MW_active_Catholyte=MW_active_Catholyte, conc_act_anode=conc_act_anode,
                                                 conc_act_catholyte=conc_act_catholyte, n_e_minus=n_e_minus,
                                                 DoD_max=DoD_max, F=F, c_active_anode=c_active_anode,
                                                 c_active_Catholyte=c_active_Catholyte,
                                                 c_SE_anode=c_SE_anode, c_SE_Catholyte=c_SE_Catholyte, OCV=OCV, i_d=i_d,
                                                 ASR=ASR, eta_sys_d=eta_sys_d,
                                                 C_fabr_sol=C_fabr_sol, C_tank_vol=C_tank_vol, c_m=c_m, c_BP=c_BP,
                                                 c_felt=c_felt,
                                                 c_frame=c_frame, c_EP=c_EP, c_IP=c_IP, c_CC=c_CC, N=N)


        C_b = calculate_system_cost(C_E, C_P, E_b_nom=E_b_nom, P_b_nom=P_b_nom)
        I0, Lt_list = financing_model(C_b=C_b, f_d=f_d, d_r=d_r, N_y=N_y, r_d_y=r_d_y)
        C_rep_t = lcos_replacement_cost(P_b_nom=P_b_nom, n_rep_P=n_rep_P, r_d_y=r_d_y, t_rep_P=t_rep_P, C_m=c_m,
                                        C_felt=c_felt, a_active=a_active)
        C_f_om_list, C_v_om_list, C_ch_om_list, E_dis_t_list, E_dis_all_list = calculate_discharged_energy_cost(
        E_b_nom=E_b_nom, Pb_nom=P_b_nom, OM_power_fixed=OM_power_fixed, OM_energy_fixed=OM_energy_fixed,
        cyc_day=cyc_day, cap_lim=cap_lim, r_CO=r_CO,
        r_ED=r_ED, r_time=r_time, N_y=N_y, DOD_max=DOD_max, r_i_y=r_i_y, r_d_y=r_d_y, eta_rt=eta_rt,
        c_el=c_el, O_cost=O_cost, om=om)

        LCOS_net, LCOS = levelized_cost(I_0=I0, Lt_list=Lt_list, C_rep_t=C_rep_t,
                                              C_f_om_list=C_f_om_list,
                                              C_v_om_list=C_v_om_list, C_ch_om_list=C_ch_om_list,
                                              E_dis_t_list=E_dis_t_list,E_dis_all_list=E_dis_all_list)
        # 3. 收集结果
        variable_parameters.append(eta_rt)
        energy_related_results.append(C_E)
        power_related_results.append(C_P)
        Capital_results.append(C_b / E_b_nom)
        LCOS_net_results.append(LCOS_net *1000)
        LCOS_results.append(LCOS *1000)

    return variable_parameters,np.array(energy_related_results),np.array(power_related_results), np.array(Capital_results), np.array(LCOS_net_results), np.array(LCOS_results)


E_b_nom = 8000   # kWh
NUM_ITERATIONS = 1000
variable_parameters,energy_related_results,power_related_results,Capital_results, LCOS_net_results, LCOS_results = Parameter_sensitive_simulation(E_b_nom = E_b_nom, num_iterations=NUM_ITERATIONS)

data = {
    'variable': variable_parameters,
    'energy': np.array(energy_related_results).flatten(),
    'power': np.array(power_related_results).flatten(),
    'capital': np.array(Capital_results).flatten(),
    'LCOS_net': np.array(LCOS_net_results).flatten(),
    'LCOS': np.array(LCOS_results).flatten()
}

df = pd.DataFrame(data)
df.to_csv('all_results.csv', index=False)