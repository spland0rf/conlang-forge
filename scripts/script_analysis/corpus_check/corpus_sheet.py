import pickle, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import corpus_load; import compound_gen as C
def draw(ax, L, title, col="#1f4e9c"):
    for P in L["strokes"]: ax.plot([p[0] for p in P], [p[1] for p in P], color=col, lw=2, solid_capstyle="round")
    for P in L.get("struct") or []: ax.plot([p[0] for p in P], [p[1] for p in P], color="#7a3fa0", lw=2)
    if L.get("bar"): ax.plot(L["bar"], [20, 20], color="#d9822b", lw=2)
    if L["sk"]["kind"] == "stem": ax.plot([L["sk"]["S"]] * 2, [20, 88], color="#c0392b", lw=2)
    if L["sk"]["kind"] == "desc": ax.plot([L["sk"]["x"]] * 2, [20, 36], color="#7a3fa0", lw=2)
    ax.set_xlim(0, 100); ax.set_ylim(100, -8); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, fontsize=6.5)
def sheet(items, path, cols=8):
    n = len(items); rows = (n + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 1.6, rows * 1.75), dpi=130)
    for a in (axs.ravel() if rows * cols > 1 else [axs]): a.axis("off")
    for ax, (L, t, c) in zip(axs.ravel(), items): ax.axis("on"); draw(ax, L, t, c)
    fig.tight_layout(); fig.savefig(path); print(path)
if __name__ == "__main__":
    res = pickle.load(open("repair_res.pkl", "rb"))
    rep = [(r, N, h) for r, N, h in res if N is not None][:16]
    items = []
    for r, N, h in rep:
        items.append((r, "S%d#%d before w%.2f" % (r["style"], r["idx"], C.white_fraction(r)), "#999999"))
        items.append((N, "after x%.2f y%.2f w%.2f" % (h[0], h[1], C.white_fraction(N)), "#1f4e9c"))
    sheet(items, "repaired_corpus.png")
    stuck = [(r, "S%d#%d w%.2f p%.2f" % (r["style"], r["idx"], C.white_fraction(r), C.primary_size(r)), "#a33") for r, N, h in res if N is None and h != "ok"][:32]
    sheet(stuck, "stuck_corpus.png")
