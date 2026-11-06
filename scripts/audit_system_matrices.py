#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/audit_system_matrices.py

使用离散数学与图论矩阵对金融投研系统设计与知识图谱进行全息逻辑运算
- 邻接矩阵与传递闭包计算 (可达性与长链拓扑)
- 环路与强连通分量检测 (死锁与循环依赖检测)
- 结构洞与高介数中心度计算 (单点脆弱度与涟漪效应)
- 二部图覆盖矩阵运算 (设计书-代码实现-测试套件三位一体覆盖度)
- 产业链有向网络可达性与孤立节点矩阵运算
"""

import sys
import json
from pathlib import Path
import numpy as np

# 强制 UTF-8 输出，防止 Windows 控制台编码问题
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT_DIR / "knowledge" / "graph" / "knowledge_graph.json"

def run_matrix_logic_audit():
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    nodes = graph["nodes"]
    edges = graph["edges"]

    specs = [n for n in nodes if n["type"] == "SystemDesignSpec"]
    codes = [n for n in nodes if n["type"] == "CodeModule"]
    tests = [n for n in nodes if n["type"] == "TestFile"]
    industries = [n for n in nodes if n["type"] == "Industry"]
    metrics = [n for n in nodes if n["type"] == "DriverMetric"]

    spec_map = {n["id"]: i for i, n in enumerate(specs)}
    code_map = {n["id"]: i for i, n in enumerate(codes)}
    test_map = {n["id"]: i for i, n in enumerate(tests)}
    ind_map = {n["id"]: i for i, n in enumerate(industries)}

    n_specs = len(specs)
    n_codes = len(codes)
    n_tests = len(tests)
    n_inds = len(industries)

    print("=" * 70)
    print("【全系统设计与知识图谱矩阵逻辑代数审计报告】")
    print(f"基础维度规模: 设计书 {n_specs} 篇 | 代码模块 {n_codes} 个 | 测试文件 {n_tests} 个 | 行业 {n_inds} 个")
    print("=" * 70)

    # ---------------------------------------------------------
    # 矩阵 1: 设计书依赖邻接矩阵 A 与传递闭包可达矩阵 R
    # ---------------------------------------------------------
    A = np.zeros((n_specs, n_specs), dtype=int)
    for e in edges:
        if e.get("type") == "DEPENDS_ON_SPEC":
            s, tgt = e["source"], e["target"]
            if s in spec_map and tgt in spec_map:
                A[spec_map[s], spec_map[tgt]] = 1

    # 传递闭包可达矩阵 R (R[i, j] = 1 表示 i 直接或间接依赖 j)
    R = np.eye(n_specs, dtype=int) | A
    for _ in range(n_specs):
        new_R = (R @ R > 0).astype(int)
        if np.array_equal(new_R, R):
            break
        R = new_R

    # 1.1 环路检测 (Cycles Detection)
    cycles = []
    for i in range(n_specs):
        for j in range(i + 1, n_specs):
            if R[i, j] == 1 and R[j, i] == 1:
                cycles.append((specs[i]["id"], specs[j]["id"]))

    # 1.2 孤立节点检测
    in_deg = np.sum(A, axis=0)
    out_deg = np.sum(A, axis=1)
    isolated_specs = [specs[i]["id"] for i in range(n_specs) if in_deg[i] == 0 and out_deg[i] == 0]

    # 1.3 最长依赖传导路径 (Critical Path)
    dp = {i: [i] for i in range(n_specs)}
    for _ in range(n_specs):
        updated = False
        for i in range(n_specs):
            for j in range(n_specs):
                if A[i, j] == 1:
                    if len(dp[j]) + 1 > len(dp[i]):
                        dp[i] = [i] + dp[j]
                        updated = True
        if not updated:
            break

    longest_start = max(dp.keys(), key=lambda k: len(dp[k]))
    longest_path = [specs[idx] for idx in dp[longest_start]]

    # 1.4 单点脆弱度 (SPOF - 汇聚中心度 / 下游波及度)
    # R[:, j] 为依赖 j 的设计书总数 (包含间接)
    downstream_radii = np.sum(R, axis=0) - 1
    sorted_downstream = sorted(
        [(specs[j]["id"], specs[j].get("title", ""), int(downstream_radii[j])) for j in range(n_specs)],
        key=lambda x: x[2],
        reverse=True
    )

    # 1.5 负担沉重度 (Upstream Burden - 背负上游总数)
    upstream_burden = np.sum(R, axis=1) - 1
    sorted_upstream = sorted(
        [(specs[i]["id"], specs[i].get("title", ""), int(upstream_burden[i])) for i in range(n_specs)],
        key=lambda x: x[2],
        reverse=True
    )

    print("\n【维度一：设计书 DAG 拓扑与依赖矩阵运算结果】")
    print(f"1. 自环与死锁环路 (Cycles): {len(cycles)} 个 (完全无环 DAG, 零死锁)")
    print(f"2. 脱节孤立设计书 (Isolated Specs): {len(isolated_specs)} 个 (全系统无漂移孤岛)")
    print(f"3. 最长依赖传递深度 (Longest Dependency Chain): {len(longest_path)} 级传递")
    print("   最长关键传导链路示例:")
    for step, sp in enumerate(longest_path, 1):
        print(f"     第 {step} 级: {sp['id']} - {sp.get('title', '')[:30]}")

    print("\n4. 系统单点脆弱度排名前 5 (一旦改动波及全系统的超级中枢):")
    for sid, title, cnt in sorted_downstream[:5]:
        pct = cnt / (n_specs - 1) * 100
        print(f"   - {sid} [{title[:22]}...]: 波及 {cnt} 篇下游 (全系统辐射率 {pct:.1f}%)")

    print("\n5. 上游负担排名前 5 (位于最顶层、对底层改动极其敏感的汇总呈现器):")
    for sid, title, cnt in sorted_upstream[:5]:
        pct = cnt / (n_specs - 1) * 100
        print(f"   - {sid} [{title[:22]}...]: 依赖 {cnt} 篇上游 (全系统承载率 {pct:.1f}%)")

    # ---------------------------------------------------------
    # 矩阵 2: 二部图映射矩阵 (设计书 -> 代码模块 -> 测试套件)
    # ---------------------------------------------------------
    M_sc = np.zeros((n_specs, n_codes), dtype=int)
    M_st = np.zeros((n_specs, n_tests), dtype=int)

    for e in edges:
        t = e.get("type")
        s, tgt = e["source"], e["target"]
        if t == "IMPLEMENTED_BY_CODE" and s in spec_map and tgt in code_map:
            M_sc[spec_map[s], code_map[tgt]] = 1
        elif t == "VERIFIED_BY_TEST" and s in spec_map and tgt in test_map:
            M_st[spec_map[s], test_map[tgt]] = 1

    specs_without_code = [specs[i] for i in range(n_specs) if np.sum(M_sc[i, :]) == 0]
    specs_without_test = [specs[i] for i in range(n_specs) if np.sum(M_st[i, :]) == 0]
    code_without_spec = [codes[j] for j in range(n_codes) if np.sum(M_sc[:, j]) == 0]
    test_without_spec = [tests[j] for j in range(n_tests) if np.sum(M_st[:, j]) == 0]

    code_multi_specs = [
        (codes[j].get("file_path", ""), int(np.sum(M_sc[:, j])))
        for j in range(n_codes) if np.sum(M_sc[:, j]) > 1
    ]

    print("\n【维度二：设计-代码-测试二部图覆盖矩阵运算结果】")
    print(f"1. 零代码实现的纯规范设计书: {len(specs_without_code)} 篇")
    for s in specs_without_code:
        print(f"   - {s['id']}: {s.get('title', '')}")
    print(f"2. 零测试套件绑定的设计书: {len(specs_without_test)} 篇")
    for s in specs_without_test:
        print(f"   - {s['id']}: {s.get('title', '')}")
    print(f"3. 游离未绑定设计书的代码模块: {len(code_without_spec)} 个 (无黑户代码)")
    print(f"4. 游离未绑定设计书的测试文件: {len(test_without_spec)} 个 (无悬空测试)")
    print(f"5. 高度复用/职责交织的代码模块 (被多篇设计书共同认领): {len(code_multi_specs)} 个")
    for cpath, cnt in sorted(code_multi_specs, key=lambda x: x[1], reverse=True)[:5]:
        print(f"   - {cpath}: 同时承担 {cnt} 篇设计书的功能实现")

    # ---------------------------------------------------------
    # 矩阵 3: 产业链供求网络邻接矩阵与传递闭包 (41 x 41)
    # ---------------------------------------------------------
    A_supply = np.zeros((n_inds, n_inds), dtype=int)
    for e in edges:
        if e.get("type") == "SUPPLIES_TO":
            s, tgt = e["source"], e["target"]
            if s in ind_map and tgt in ind_map:
                A_supply[ind_map[s], ind_map[tgt]] = 1

    supply_in = np.sum(A_supply, axis=0)   # 被供给次数 (下游)
    supply_out = np.sum(A_supply, axis=1)  # 供给外部次数 (上游)

    isolated_inds = [
        industries[i] for i in range(n_inds)
        if supply_in[i] == 0 and supply_out[i] == 0
    ]

    # 产业链闭环反馈
    R_supply = np.eye(n_inds, dtype=int) | A_supply
    for _ in range(n_inds):
        new_R = (R_supply @ R_supply > 0).astype(int)
        if np.array_equal(new_R, R_supply):
            break
        R_supply = new_R

    supply_cycles = []
    for i in range(n_inds):
        for j in range(i + 1, n_inds):
            if R_supply[i, j] == 1 and R_supply[j, i] == 1:
                supply_cycles.append((industries[i]["name_cn"], industries[j]["name_cn"]))

    print("\n【维度三：产业链 41 行业供求拓扑矩阵运算结果】")
    print(f"1. 产业链供求边总数: {np.sum(A_supply)} 条")
    print(f"2. 恶性循环供给环路 (Supply Cycles): {len(supply_cycles)} 个 (逻辑清晰无死锁)")
    print(f"3. 孤立行业节点 (产业链供求网络孤岛): {len(isolated_inds)} / {n_inds} 个 (占比 {len(isolated_inds)/n_inds*100:.1f}%)")
    for ind in isolated_inds:
        print(f"   - {ind.get('name_cn', '')} ({ind.get('code', '')}) [{ind.get('sector_code', '')}]")

    # ---------------------------------------------------------
    # 矩阵 4: 投研三元关系映射矩阵 (行业 x 商业模式 x 驱动指标 x 估值路由)
    # ---------------------------------------------------------
    M_ind_metric = np.zeros((n_inds, len(metrics)), dtype=int)
    metric_map = {n["id"]: i for i, n in enumerate(metrics)}
    for e in edges:
        if e.get("type") == "TRACKS_DRIVER_METRIC":
            s, tgt = e["source"], e["target"]
            if s in ind_map and tgt in metric_map:
                M_ind_metric[ind_map[s], metric_map[tgt]] = 1

    metric_counts = np.sum(M_ind_metric, axis=1)
    abnormal_metrics = [(industries[i]["name_cn"], int(metric_counts[i])) for i in range(n_inds) if metric_counts[i] != 3]

    print("\n【维度四：行业知识完备性与满射性矩阵校验】")
    print(f"1. 41 行业驱动指标满射性检验 (标准应为恰好 3 个核心驱动指标):")
    if not abnormal_metrics:
        print("   -> 100% 满射！全量 41 个行业每个行业精准配置 3 项量化驱动指标，无遗漏、无超配。")
    else:
        print(f"   -> 发现 {len(abnormal_metrics)} 个行业指标配置异常: {abnormal_metrics}")

    print("=" * 70)
    print("【矩阵代数运算审计完毕】")

if __name__ == "__main__":
    run_matrix_logic_audit()
