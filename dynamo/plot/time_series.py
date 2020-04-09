# include pseudotime and predict cell trajectory
import statsmodels.api as sm
import numpy as np
from scipy.sparse import issparse
from scipy.interpolate import interp1d
from ..tools.utils import fetch_exprs, update_dict
from .utils import save

from ..docrep import DocstringProcessor

docstrings = DocstringProcessor()


@docstrings.get_sectionsf("kin_curves")
def kinetic_curves(
    adata,
    genes,
    mode="vector_field",
    basis=None,
    layer="X",
    project_back_to_high_dim=True,
    time="pseudotime",
    dist_threshold=1e-10,
    ncol=4,
    color=None,
    c_palette="Set2",
    standard_scale=0,
    save_show_or_return='show',
    save_kwargs={},
):
    """Plot the gene expression dynamics over time (pseudotime or inferred real time) as kinetic curves.

    Parameters
    ----------
        adata: :class:`~anndata.AnnData`
            an Annodata object.
        genes: `list`
            The gene names whose gene expression will be faceted.
        mode: `str` (default: `vector_field`)
            Which data mode will be used, either vector_field or pseudotime. if mode is vector_field, the trajectory predicted by
            vector field function will be used, otherwise pseudotime trajectory (defined by time argument) will be used.
        basis: `str` or None (default: `None`)
            The embedding data used for drawing the kinetic gene expression curves, only used when mode is `vector_field`.
        layer: `str` (default: X)
            Which layer of expression value will be used. Not used if mode is `vector_field`.
        project_back_to_high_dim: `bool` (default: `False`)
            Whether to map the coordinates in low dimension back to high dimension to visualize the gene expression curves,
            only used when mode is `vector_field` and basis is not `X`. Currently only works when basis is 'pca' and 'umap'.
        color: `list` or None (default: None)
            A list of attributes of cells (column names in the adata.obs) will be used to color cells.
        time: `str` (default: `pseudotime`)
            The .obs column that will be used for timing each cell, only used when mode is `vector_field`.
        dist_threshold: `float` or None (default: 1e-10)
            The threshold for the distance between two points in the gene expression state, i.e, x(t), x(t+1). If below this threshold,
            we assume steady state is achieved and those data points will not be considered.
        ncol: `int` (default: 4)
            Number of columns in each facet grid.
        c_palette: Name of color_palette supported in seaborn color_palette function (default: None)
            The color map function to use.
        standard_scale: `int` (default: 1)
            Either 0 (rows) or 1 (columns). Whether or not to standardize that dimension, meaning for each row or column,
            subtract the minimum and divide each by its maximum.
        save_show_or_return: {'show', 'save', 'return'} (default: `show`)
            Whether to save, show or return the figure.
        save_kwargs: `dict` (default: `{}`)
            A dictionary that will passed to the save function. By default it is an empty dictionary and the save function
            will use the {"path": None, "prefix": 'kinetic_curves', "dpi": None, "ext": 'pdf', "transparent": True, "close":
            True, "verbose": True} as its parameters. Otherwise you can provide a dictionary that properly modify those keys
            according to your needs.

    Returns
    -------
        Nothing but plots the kinetic curves that shows the gene expression dynamics over time.
    """

    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt

    exprs, valid_genes, time = fetch_exprs(
        adata, basis, layer, genes, time, mode, project_back_to_high_dim
    )

    Color = np.empty((0, 1))
    if color is not None and mode is not "vector_field":
        color = list(set(color).intersection(adata.obs.keys()))
        Color = (
            adata.obs[color].values.T.flatten() if len(color) > 0 else np.empty((0, 1))
        )

    exprs = exprs.A if issparse(exprs) else exprs
    if standard_scale is not None:
        exprs = (exprs - np.min(exprs, axis=standard_scale)) / np.ptp(
            exprs, axis=standard_scale
        )

    time = np.sort(time)
    exprs = exprs[np.argsort(time), :]

    if dist_threshold is not None:
        valid_ind = list(
            np.where(np.sum(np.diff(exprs, axis=0) ** 2, axis=1) > dist_threshold)[0]
            + 1
        )
        valid_ind.insert(0, 0)
        exprs = exprs[valid_ind, :]
        time = time[valid_ind]

    exprs_df = pd.DataFrame(
        {
            "Time": np.repeat(time, len(valid_genes)),
            "Expression": exprs.flatten(),
            "Gene": np.tile(valid_genes, len(time)),
        }
    )
    exprs_df = exprs_df.query("Gene in @genes")

    if exprs_df.shape[0] == 0:
        raise Exception(
            "No genes you provided are detected. Please make sure the genes provided are from the genes "
            "used for vector field reconstructed when layer is set."
        )

    # https://stackoverflow.com/questions/43920341/python-seaborn-facetgrid-change-titles
    if len(Color) > 0:
        exprs_df["Color"] = np.repeat(Color, len(valid_genes))
        g = sns.relplot(
            x="Time",
            y="Expression",
            data=exprs_df,
            col="Gene",
            hue="Color",
            palette=sns.color_palette(c_palette),
            col_wrap=ncol,
            kind="line",
            facet_kws={"sharex": True, "sharey": False},
        )
    else:
        g = sns.relplot(
            x="Time",
            y="Expression",
            data=exprs_df,
            col="Gene",
            col_wrap=ncol,
            kind="line",
            facet_kws={"sharex": True, "sharey": False},
        )

    if save_show_or_return == "save":
        s_kwargs = {"path": None, "prefix": 'kinetic_curves', "dpi": None,
                    "ext": 'pdf', "transparent": True, "close": True, "verbose": True}
        s_kwargs = update_dict(s_kwargs, save_kwargs)

        save(**s_kwargs)
    elif save_show_or_return == "show":
        plt.tight_layout()
        plt.show()
    elif save_show_or_return == "return":
        return g


docstrings.delete_params("kin_curves.parameters", "ncol", "color", "c_palette")


@docstrings.with_indent(4)
def kinetic_heatmap(
    adata,
    genes,
    mode="vector_field",
    basis=None,
    layer="X",
    project_back_to_high_dim=True,
    time="pseudotime",
    dist_threshold=1e-10,
    color_map="BrBG",
    gene_order_method='half_max_ordering',
    show_colorbar=False,
    cluster_row_col=[False, False],
    figsize=(11.5, 6),
    standard_scale=1,
    save_show_or_return='show',
    save_kwargs={},
    **kwargs
):
    """Plot the gene expression dynamics over time (pseudotime or inferred real time) in a heatmap.

    Parameters
    ----------
        %(kin_curves.parameters.no_ncol|color|c_palette)s
        color_map: `str` (default: `BrBG`)
            Color map that will be used to color the gene expression. If `half_max_ordering` is True, the
            color map need to be divergent, good examples, include `BrBG`, `RdBu_r` or `coolwarm`, etc.
        gene_order_method: `str` (default: `half_max_ordering`) [`half_max_ordering`, `maximum`]
            Supports two different methods for ordering genes when plotting the heatmap: either `half_max_ordering`,
            or `maximum`. For `half_max_ordering`, it will order genes into up, down and transit groups by the half
            max ordering algorithm (HA Pliner, et. al, Molecular cell 71 (5), 858-871. e8). While for `maximum`,
            it will order by the position of the highest gene expression.
        show_colorbar: `bool` (default: `False`)
            Whether to show the color bar.
        cluster_row_col: `[bool, bool]` (default: `[False, False]`)
            Whether to cluster the row or columns.
        figsize: `str` (default: `(11.5, 6)`
            Size of figure
        standard_scale: `int` (default: 1)
            Either 0 (rows, cells) or 1 (columns, genes). Whether or not to standardize that dimension, meaning for each row or column,
            subtract the minimum and divide each by its maximum.
        save_show_or_return: {'show', 'save', 'return'} (default: `show`)
            Whether to save, show or return the figure.
        save_kwargs: `dict` (default: `{}`)
            A dictionary that will passed to the save function. By default it is an empty dictionary and the save function
            will use the {"path": None, "prefix": 'kinetic_heatmap', "dpi": None, "ext": 'pdf', "transparent": True, "close":
            True, "verbose": True} as its parameters. Otherwise you can provide a dictionary that properly modify those keys
            according to your needs.
        kwargs:
            All other keyword arguments are passed to heatmap(). Currently `xticklabels=False, yticklabels='auto'` is passed
            to heatmap() by default.

    Returns
    -------
        Nothing but plots a heatmap that shows the gene expression dynamics over time.
    """

    import pandas as pd
    import seaborn as sns
    import matplotlib.pyplot as plt

    exprs, valid_genes, time = fetch_exprs(
        adata, basis, layer, genes, time, mode, project_back_to_high_dim
    )

    exprs = exprs.A if issparse(exprs) else exprs

    if dist_threshold is not None:
        valid_ind = list(
            np.where(np.sum(np.diff(exprs, axis=0) ** 2, axis=1) > dist_threshold)[0]
            + 1
        )
        valid_ind.insert(0, 0)
        exprs = exprs[valid_ind, :]

    if gene_order_method == "half_max_ordering":
        time, all, valid_ind, gene_idx = _half_max_ordering(
            exprs.T, time, mode=mode, interpolate=True, spaced_num=100
        )
        all, genes = all[np.isfinite(all.sum(1)), :], np.array(valid_genes)[gene_idx][np.isfinite(all.sum(1))]

        df = pd.DataFrame(all, index=genes)
    elif gene_order_method == 'maximum':
        exprs = lowess_smoother(time, exprs.T, spaced_num=100)
        exprs = exprs[np.isfinite(exprs.sum(1)), :]

        if standard_scale is not None:
            exprs = (exprs - np.min(exprs, axis=standard_scale)[:, None]) / np.ptp(
                exprs, axis=standard_scale
            )[:, None]
        max_sort = np.argsort(np.argmax(exprs, axis=1))
        df = pd.DataFrame(exprs[max_sort, :], index=np.array(valid_genes)[max_sort])
    else:
        raise Exception('gene order_method can only be either half_max_ordering or maximum')

    heatmap_kwargs = dict(xticklabels=False, yticklabels="auto")
    if kwargs is not None:
        heatmap_kwargs = update_dict(heatmap_kwargs, kwargs)

    sns_heatmap = sns.clustermap(
        df,
        col_cluster=cluster_row_col[0],
        row_cluster=cluster_row_col[1],
        cmap=color_map,
        figsize=figsize,
        **heatmap_kwargs
    )
    if not show_colorbar: sns_heatmap.cax.set_visible(False)

    if save_show_or_return == "save":
        s_kwargs = {"path": None, "prefix": 'kinetic_heatmap', "dpi": None,
                    "ext": 'pdf', "transparent": True, "close": True, "verbose": True}
        s_kwargs = update_dict(s_kwargs, save_kwargs)

        save(**s_kwargs)
    elif save_show_or_return == "show":
        if show_colorbar:
            plt.subplots_adjust(right=0.85)
        plt.tight_layout()
        plt.show()
    elif save_show_or_return == "return":
        return sns_heatmap


def _half_max_ordering(exprs, time, mode, interpolate=False, spaced_num=100):
    """Implement the half-max ordering algorithm from HA Pliner, Molecular Cell, 2018.

    Parameters
    ----------
        exprs: `np.ndarray`
            The gene expression matrix (ngenes x ncells) ordered along time (either pseudotime or inferred real time).
        time: `np.ndarray`
            Pseudotime or inferred real time.
        mode: `str` (default: `vector_field`)
            Which data mode will be used, either vector_field or pseudotime. if mode is vector_field, the trajectory predicted by
            vector field function will be used, otherwise pseudotime trajectory (defined by time argument) will be used.
        interpolate: `bool` (default: `False`)
            Whether to interpolate the data when performing the loess fitting.
        spaced_num: `float` (default: `100`)
            The number of points on the loess fitting curve.

    Returns
    -------
        time: `np.ndarray`
            The time at which the loess is evaluated.
        all: `np.ndarray`
            The ordered smoothed, scaled expression matrix, the first group is up, then down, followed by the transient gene groups.
        valid_ind: `np.ndarray`
            The indices of valid genes that Loess smoothed.
        gene_idx: `np.ndarray`
            The indices of genes that are used for the half-max ordering plot.
    """

    if mode == "vector_field":
        interpolate = False

    gene_num = exprs.shape[0]
    cell_num = spaced_num if interpolate else exprs.shape[1]
    if interpolate:
        hm_mat_scaled, hm_mat_scaled_z = (
            np.zeros((gene_num, cell_num)),
            np.zeros((gene_num, cell_num)),
        )
    else:
        hm_mat_scaled, hm_mat_scaled_z = np.zeros_like(exprs), np.zeros_like(exprs)

    transient, trans_max, half_max = (
        np.zeros(gene_num),
        np.zeros(gene_num),
        np.zeros(gene_num),
    )

    tmp = lowess_smoother(time, exprs, spaced_num) if interpolate else exprs

    for i in range(gene_num):
        hm_mat_scaled[i] = tmp[i] - np.min(tmp[i])
        hm_mat_scaled[i] = hm_mat_scaled[i] / np.max(hm_mat_scaled[i])
        scale_tmp = (tmp[i] - np.mean(tmp[i])) / np.std(tmp[i]) # scale in R
        hm_mat_scaled_z[i] = scale_tmp

        count, current = 0, hm_mat_scaled_z[i, 0] < 0  # check this
        for j in range(cell_num):
            if not (scale_tmp[j] < 0 == current):
                count = count + 1
                current = scale_tmp[j] < 0

        half_max[i] = np.argmax(np.abs(scale_tmp - 0.5))
        transient[i] = count
        trans_max[i] = np.argsort(-scale_tmp)[0]

    begin = np.arange(max([5, 0.05 * cell_num]))
    end = np.arange(exprs.shape[1] - max([5, 0.05 * cell_num]), cell_num)
    trans_indx = np.logical_and(
        transient > 1, not [i in np.concatenate((begin, end)) for i in trans_max]
    )

    trans_idx, trans, half_max_trans = (
        np.where(trans_indx)[0],
        hm_mat_scaled[trans_indx, :],
        half_max[trans_indx],
    )
    nt_idx, nt = np.where(~trans_indx)[0], hm_mat_scaled[~trans_indx, :]
    up_idx, up, half_max_up = (
        np.where(nt[:, 0] < nt[:, -1])[0],
        nt[nt[:, 0] < nt[:, -1], :],
        half_max[nt[:, 0] < nt[:, -1]],
    )
    down_indx, down, half_max_down = (
        np.where(nt[:, 0] >= nt[:, -1])[0],
        nt[nt[:, 0] >= nt[:, -1], :],
        half_max[nt[:, 0] >= nt[:, -1]],
    )

    trans, up, down = (
        trans[np.argsort(half_max_trans), :],
        up[np.argsort(half_max_up), :],
        down[np.argsort(half_max_down), :],
    )

    all = np.vstack((up, down, trans))
    gene_idx = np.hstack(
        (
            nt_idx[up_idx][np.argsort(half_max_up)],
            nt_idx[down_indx][np.argsort(half_max_down)],
            trans_idx,
        )
    )

    return time, all, np.isfinite(nt[:, 0]) & np.isfinite(nt[:, -1]), gene_idx


def lowess_smoother(time, exprs, spaced_num):
    gene_num = exprs.shape[0]
    res = np.zeros((gene_num, spaced_num))

    for i in range(gene_num):
        x = exprs[i]

        lowess = sm.nonparametric.lowess
        tmp = lowess(x, time, frac=.3)
        # run scipy's interpolation.
        f = interp1d(tmp[:, 0], tmp[:, 1], bounds_error=False)

        time_linspace = np.linspace(np.min(time), np.max(time), spaced_num)
        res[i, :] = f(time_linspace)

    return res
