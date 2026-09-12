"""Figure 17 -- task success and decision accuracy in each configuration."""
import _data as D, _table as T


def build():
    rows_in = D.load()
    per = lambda f: D.cell_means(D.by_task(rows_in, field=f))
    s, d = per("success_strict"), per("decision_correct")
    rows = [[f"{c}  {D.DESIGN[c]} / {D.DEPLOY[c]}", f"{s[c]:.3f}", f"{d[c]:.3f}", "240"]
            for c in ["C1", "C2", "C3", "C4"]]
    T.render("fig17_configurations",
             ["configuration", "task success", "decision accuracy", "n"], rows,
             "Each configuration is 48 tasks × 5 repetitions. Task success is the primary measure,\n"
             "with partial credit counted as failure.",
             widths=[3.4, 1.7, 2.2, 0.8])


if __name__ == "__main__":
    build()
