"""
Outils communs aux graphes « qui souffrent ensemble » (axe 8 : secteurs, axe 9 : départements).

Démarche (TP3 et TP4) : courbes mensuelles -> évolution sur 12 mois -> similarité -> seuil
-> graphe -> small world, centralités, communautés de Louvain -> node2vec -> carte 2D.
"""
from __future__ import annotations

import random

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from networkx.algorithms.community import louvain_communities, modularity
from sklearn.metrics import adjusted_rand_score

# Couleurs du design system (app/design.py)
BLEU, GRIS, ENCRE, TITRE = "#2a78d6", "#898781", "#52514e", "#0b0b0b"
COULEURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
AUTRE = "#b5b3ab"

plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": ENCRE,
                     "xtick.color": GRIS, "ytick.color": GRIS, "axes.grid": True, "grid.color": "#e1e0d9",
                     "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 110})


# --------------------------------------------------------------------------- préparation
def evolution_12_mois(series: pd.DataFrame) -> pd.DataFrame:
    """Défaillances des 12 derniers mois / celles des 12 mois d'avant - 1 (une colonne par entité)."""
    cumul = series.rolling(12).sum()
    return (cumul / cumul.shift(12) - 1).dropna()


def triangle(df: pd.DataFrame) -> pd.Series:
    """Les valeurs au-dessus de la diagonale d'une matrice carrée (une par paire)."""
    i, j = np.triu_indices(len(df), k=1)
    return pd.Series(df.to_numpy()[i, j], index=pd.MultiIndex.from_arrays([df.index[i], df.columns[j]], names=["a", "b"]))


# --------------------------------------------------------------------------- seuil
def construire_graphe(S: pd.DataFrame, seuil: float, garder_isoles=False) -> nx.Graph:
    """Arête si similarité >= seuil ; sans boucles ni (par défaut) nœuds isolés."""
    G = nx.from_pandas_adjacency(S.where(S >= seuil, 0))
    G.remove_edges_from(nx.selfloop_edges(G))
    if not garder_isoles:
        G.remove_nodes_from(list(nx.isolates(G)))
    return G


def courbe_seuils(S: pd.DataFrame, seuils) -> pd.DataFrame:
    """Pour chaque seuil : nœuds gardés, arêtes, composantes, communautés et modularité (Louvain)."""
    lignes = []
    for seuil in seuils:
        G = construire_graphe(S, seuil)
        ligne = {"seuil": seuil, "nœuds gardés": G.number_of_nodes(), "arêtes": G.number_of_edges(),
                 "composantes": nx.number_connected_components(G) if G.number_of_nodes() else 0}
        if G.number_of_edges():
            comms = louvain_communities(G, weight="weight", seed=0)
            ligne["communautés"] = len(comms)
            ligne["modularité"] = modularity(G, comms, weight="weight")
        lignes.append(ligne)
    return pd.DataFrame(lignes).set_index("seuil")


def coude(x, y) -> float:
    """Méthode Kneedle : le point le plus éloigné de la droite entre les deux extrémités de la courbe."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    xn = (x - x.min()) / (x.max() - x.min())
    yn = (y - y.min()) / (y.max() - y.min())
    a = np.array([xn[-1] - xn[0], yn[-1] - yn[0]])
    d = np.abs(a[0] * (yn - yn[0]) - a[1] * (xn - xn[0])) / np.linalg.norm(a)
    return float(x[np.argmax(d)])


def tracer_coudes(courbes: pd.DataFrame, coudes: dict, unite="nœuds gardés"):
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, m in zip(axes, [unite, "arêtes", "modularité"]):
        c = courbes[m].dropna()
        ax.plot(c.index, c.values, color=BLEU, lw=2)
        ax.set_title(m.capitalize(), loc="left", fontsize=11, color=TITRE)
        ax.set_xlabel("seuil")
        if m in coudes:
            ax.axvline(coudes[m], color=GRIS, lw=1)
            ax.annotate(f"coude : {coudes[m]:.2f}".replace(".", ","), (coudes[m], c.max()),
                        xytext=(6, -4), textcoords="offset points", color=ENCRE, fontsize=9, va="top")
    fig.tight_layout()
    plt.show()


# --------------------------------------------------------------------------- descripteurs
def small_world(G: nx.Graph, n_aleatoires=20) -> tuple[pd.DataFrame, float]:
    """Compare clustering et plus courts chemins à des graphes aléatoires de même taille (indice sigma)."""
    plus_grand = G.subgraph(max(nx.connected_components(G), key=len))
    C, L = nx.average_clustering(G), nx.average_shortest_path_length(plus_grand)
    al = [nx.gnm_random_graph(G.number_of_nodes(), G.number_of_edges(), seed=s) for s in range(n_aleatoires)]
    al = [A for A in al if nx.is_connected(A)]
    C_al = np.mean([nx.average_clustering(A) for A in al])
    L_al = np.mean([nx.average_shortest_path_length(A) for A in al])
    tableau = pd.DataFrame({"notre graphe": [C, L, nx.diameter(plus_grand)],
                            f"graphes aléatoires ({len(al)})": [C_al, L_al, np.mean([nx.diameter(A) for A in al])]},
                           index=["clustering moyen", "plus court chemin moyen", "diamètre"])
    return tableau, (C / C_al) / (L / L_al)


def centralites(G: nx.Graph) -> pd.DataFrame:
    return pd.DataFrame({
        "degré": pd.Series(dict(G.degree())),
        "intermédiarité": pd.Series(nx.betweenness_centrality(G)),
        "pagerank": pd.Series(nx.pagerank(G, weight="weight")),
    })


# --------------------------------------------------------------------------- communautés
def partition(G: nx.Graph, resolution: float, seed=0):
    """Communautés de Louvain triées par taille, et dictionnaire nœud -> numéro (1 = la plus grande)."""
    comms = sorted(louvain_communities(G, weight="weight", resolution=resolution, seed=seed), key=len, reverse=True)
    return comms, {n: i + 1 for i, c in enumerate(comms) for n in c}


def stabilite_louvain(G: nx.Graph, resolutions, n_graines=20) -> pd.DataFrame:
    """Pour chaque résolution : nombre de communautés, modularité et stabilité (ARI moyen entre graines)."""
    noeuds = list(G)
    lignes = []
    for res in resolutions:
        parts = [partition(G, res, s) for s in range(n_graines)]
        etiquettes = [[p[1][n] for n in noeuds] for p in parts]
        ari = [adjusted_rand_score(etiquettes[a], etiquettes[b])
               for a in range(n_graines) for b in range(a + 1, n_graines)]
        nb = [len(p[0]) for p in parts]
        lignes.append({"résolution": res, "communautés (min-max)": f"{min(nb)}-{max(nb)}",
                       "modularité moyenne": np.mean([modularity(G, p[0], weight="weight") for p in parts]),
                       "ARI moyen entre graines": np.mean(ari)})
    return pd.DataFrame(lignes).set_index("résolution")


def partition_consensus(G: nx.Graph, resolution: float, n_graines=20):
    """La partition la plus « typique » : celle qui ressemble le plus (ARI moyen) à toutes les autres graines."""
    noeuds = list(G)
    parts = [partition(G, resolution, s) for s in range(n_graines)]
    etiquettes = [[p[1][n] for n in noeuds] for p in parts]
    score = [np.mean([adjusted_rand_score(e, f) for f in etiquettes]) for e in etiquettes]
    meilleure = int(np.argmax(score))
    return parts[meilleure][0], parts[meilleure][1], meilleure


def tracer_evolution_communautes(evolution: pd.DataFrame, comms, nom_de, titre):
    """Petits multiples : évolution moyenne de chaque communauté (bleu) contre l'ensemble (gris)."""
    n = len(comms)
    ncol = min(4, n)
    fig, axes = plt.subplots((n + ncol - 1) // ncol, ncol, figsize=(3.5 * ncol, 2.9 * ((n + ncol - 1) // ncol)),
                             sharex=True, sharey=True, squeeze=False)
    tous = [x for c in comms for x in c]
    dates = pd.to_datetime(evolution.index)
    ensemble = 100 * evolution[tous].mean(axis=1)
    for ax, (i, c) in zip(axes.flat, enumerate(comms, 1)):
        ax.plot(dates, ensemble.values, color="#c3c2b7", lw=1.5, label="ensemble du graphe")
        ax.plot(dates, 100 * evolution[sorted(c)].mean(axis=1).values, color=COULEURS[(i - 1) % len(COULEURS)],
                lw=2, label="la communauté")
        ax.axhline(0, color="#c3c2b7", lw=0.8)
        ax.set_title(f"{i}. {nom_de(c)[:32]} ({len(c)})", loc="left", fontsize=9, color=TITRE)
        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    axes.flat[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle(titre, x=0.01, ha="left", fontsize=11, color=TITRE)
    fig.tight_layout()
    plt.show()


def dessiner_graphe(G, pos, communaute, taille, a_nommer, nom_de, titre, figsize=(13, 9)):
    fig, ax = plt.subplots(figsize=figsize)
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.12, edge_color=GRIS)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=[taille[n] for n in G],
                           node_color=[COULEURS[(communaute[n] - 1) % len(COULEURS)] for n in G],
                           edgecolors="#fcfcfb", linewidths=1.5)
    for n, (x, y) in pos.items():
        if n in a_nommer:
            ax.annotate(nom_de(n)[:30], (x, y), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8,
                        color=ENCRE, bbox=dict(boxstyle="round,pad=0.15", fc="#fcfcfb", ec="none", alpha=0.85))
    for i in range(max(communaute.values())):
        ax.scatter([], [], s=60, color=COULEURS[i % len(COULEURS)], label=f"Communauté {i + 1}")
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    ax.set_axis_off()
    ax.set_title(titre, loc="left", fontsize=11, color=TITRE)
    plt.show()


# --------------------------------------------------------------------------- node2vec
def marches_node2vec(G, n_marches=10, longueur=40, p=1.0, q=1.0, seed=0):
    """Marches aléatoires node2vec (même code qu'au TP4)."""
    rng = random.Random(seed)
    voisins_de = {u: list(G[u]) for u in G}
    noeuds, marches = list(G), []
    for _ in range(n_marches):
        rng.shuffle(noeuds)
        for depart in noeuds:
            marche = [depart]
            while len(marche) < longueur:
                ns = voisins_de[marche[-1]]
                if len(marche) == 1:
                    marche.append(rng.choice(ns))
                    continue
                prec = marche[-2]
                poids = [1 / p if x == prec else 1 if G.has_edge(x, prec) else 1 / q for x in ns]
                marche.append(rng.choices(ns, weights=poids)[0])
            marches.append(marche)
    return marches


def node2vec_tsne(G, dimensions=8, perplexite=10, seed=0):
    """node2vec (marches + Word2Vec) puis t-SNE en 2D. Renvoie (noeuds, vecteurs, coordonnées 2D)."""
    from gensim.models import Word2Vec
    from sklearn.manifold import TSNE

    marches = marches_node2vec(G, seed=seed)
    w2v = Word2Vec(marches, vector_size=dimensions, window=5, min_count=1, sg=1, workers=1, seed=seed, epochs=5)
    noeuds = list(G)
    vecteurs = np.array([w2v.wv[n] for n in noeuds])
    carte = TSNE(n_components=2, perplexity=perplexite, init="pca", random_state=seed).fit_transform(vecteurs)
    return noeuds, vecteurs, carte


def accord_voisins(carte, etiquettes, k=3) -> float:
    """Part des k plus proches voisins (sur la carte) qui sont dans la même communauté."""
    from sklearn.neighbors import NearestNeighbors
    voisins = NearestNeighbors(n_neighbors=k + 1).fit(carte).kneighbors(carte, return_distance=False)[:, 1:]
    etiquettes = np.asarray(etiquettes)
    return float((etiquettes[voisins] == etiquettes[:, None]).mean())


# --------------------------------------------------------------------------- cartes des départements
DOM = {"971": "Guadeloupe", "972": "Martinique", "973": "Guyane", "974": "La Réunion", "976": "Mayotte"}


def charger_departements(chemin):
    """GeoJSON des départements -> (noms {code: nom}, polygones {code: [tableaux de points]})."""
    import json
    geo = json.load(open(chemin, encoding="utf-8"))
    noms, polys = dict(DOM), {}
    for f in geo["features"]:
        code = f["properties"]["code"]
        noms[code] = f["properties"]["nom"]
        g = f["geometry"]
        anneaux = g["coordinates"] if g["type"] == "Polygon" else [p[0] for p in g["coordinates"]]
        if g["type"] == "Polygon":
            anneaux = [g["coordinates"][0]]
        polys[code] = [np.asarray(a) for a in anneaux]
    return noms, polys


def voisins_geographiques(polys, decimales=3) -> set:
    """Paires de départements qui ont une frontière commune (des sommets en commun dans le GeoJSON)."""
    points = {c: {(round(x, decimales), round(y, decimales)) for a in anneaux for x, y in a} for c, anneaux in polys.items()}
    codes = list(points)
    return {(a, b) for i, a in enumerate(codes) for b in codes[i + 1:] if len(points[a] & points[b]) >= 2}


def carte_departements(polys, couleur_de, titre, legende=None, ax=None):
    """Dessine les départements de métropole, chacun avec la couleur couleur_de(code) (gris si absent)."""
    from matplotlib.collections import PolyCollection
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))
    formes, couleurs = [], []
    for code, anneaux in polys.items():
        for a in anneaux:
            formes.append(a)
            couleurs.append(couleur_de(code) or "#e9e8e3")
    ax.add_collection(PolyCollection(formes, facecolors=couleurs, edgecolors="#fcfcfb", linewidths=0.6))
    ax.autoscale_view()
    ax.set_aspect(1.45)
    ax.set_axis_off()
    ax.set_title(titre, loc="left", fontsize=11, color=TITRE)
    if legende:
        for lib, coul in legende:
            ax.scatter([], [], s=80, marker="s", color=coul, label=lib)
        ax.legend(frameon=False, loc="lower left", fontsize=8)
    return ax


# --------------------------------------------------------------------------- choix du nombre de communautés
def balayage_resolution(G: nx.Graph, gammas, n_graines=50) -> tuple[pd.DataFrame, dict]:
    """Pour chaque résolution γ : Louvain avec n_graines graines.
    Renvoie un tableau (modularité moyenne, nombre de communautés le plus fréquent, stabilité ARI)
    et toutes les partitions {γ: [(communautés, modularité), ...]}."""
    noeuds = list(G)
    lignes, toutes = [], {}
    for g in gammas:
        parts = []
        for s in range(n_graines):
            comms = sorted(louvain_communities(G, weight="weight", resolution=g, seed=s), key=len, reverse=True)
            parts.append((comms, modularity(G, comms, weight="weight")))
        toutes[g] = parts
        nb = pd.Series([len(c) for c, _ in parts])
        etiq = [[next(i for i, c in enumerate(comms) if n in c) for n in noeuds] for comms, _ in parts]
        ari = [adjusted_rand_score(etiq[a], etiq[b]) for a in range(n_graines) for b in range(a + 1, n_graines)]
        lignes.append({"résolution": g, "modularité moyenne": np.mean([q for _, q in parts]),
                       "nombre le plus fréquent": int(nb.mode().iloc[0]),
                       "part des graines avec ce nombre": (nb == nb.mode().iloc[0]).mean(),
                       "répartition du nombre": dict(sorted(nb.value_counts().items())),
                       "ARI moyen entre graines": np.mean(ari)})
    return pd.DataFrame(lignes).set_index("résolution"), toutes


def regle_communautes(tableau: pd.DataFrame, toutes: dict):
    """La règle en 3 étapes :
    1. γ = celui qui maximise la modularité moyenne ;
    2. nombre de communautés = le plus fréquent à ce γ ;
    3. parmi les graines qui donnent ce nombre, le découpage de meilleure modularité."""
    gamma = float(tableau["modularité moyenne"].idxmax())
    nombre = int(tableau.loc[gamma, "nombre le plus fréquent"])
    candidats = [(c, q) for c, q in toutes[gamma] if len(c) == nombre]
    comms, q = max(candidats, key=lambda x: x[1])
    return gamma, nombre, comms, {n: i + 1 for i, c in enumerate(comms) for n in c}, q


def tracer_balayage(tableau: pd.DataFrame, gamma_retenu: float):
    """Modularité moyenne selon γ (gauche) et répartition du nombre de communautés (droite)."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
    axes[0].plot(tableau.index, tableau["modularité moyenne"], color=BLEU, marker="o", lw=2)
    axes[0].axvline(gamma_retenu, color=GRIS, lw=1)
    axes[0].set_xlabel("résolution γ")
    axes[0].set_title("Modularité moyenne (50 graines)", loc="left", fontsize=11, color=TITRE)
    for g, rep in tableau["répartition du nombre"].items():
        total = sum(rep.values())
        for n, k in rep.items():
            axes[1].scatter(g, n, s=12 + 400 * k / total, color=BLEU if g == gamma_retenu else "#9ec5f4",
                            edgecolors="#fcfcfb", linewidths=1, zorder=3)
    axes[1].set_xlabel("résolution γ")
    axes[1].set_ylabel("nombre de communautés")
    axes[1].set_title("Nombre de communautés obtenu (taille du point = nombre de graines)", loc="left", fontsize=11,
                      color=TITRE)
    fig.tight_layout()
    plt.show()
