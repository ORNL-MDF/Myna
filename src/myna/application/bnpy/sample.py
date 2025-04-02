import numpy as np


def get_representative_distribution(
    data,
    n0=1000,
    dn=1000,
    conv_abs=1e-3,
    conv_rel=1e-1,
    conv_count=3,
    bins=10,
    verbose=False,
):

    # Load app-specific dependencies
    try:
        import ot
    except ImportError:
        raise ImportError(
            'Myna bnpy app requires "pip install .[bnpy]" optional dependencies!'
        )

    # Initialize convergence criteria
    residue_rel = 1e6
    residue_abs = 1e6
    consecutive_counter = 0
    wasserstein_last = 1e6
    iteration = 0
    distances = []

    # Get data range
    data_range = []
    dims = data.shape[1]
    for i in range(dims):
        data_range.append(
            (
                min(np.min(data[:, i]), np.min(data[:, i])),
                max(np.max(data[:, i]), np.max(data[:, i])),
            )
        )

    all_data_sampled = False
    while (consecutive_counter <= conv_count) and (not all_data_sampled):

        # Randomly sample from dataset
        n_samples = n0 + dn * iteration
        if n_samples > data.shape[0]:
            n_samples = data.shape[0]
            all_data_sampled = True
        sample = data[np.random.choice(data.shape[0], n_samples, replace=False)]

        # Compute the histograms
        hist_data = np.histogramdd(data, bins=bins, range=data_range, density=True)
        hist_sample = np.histogramdd(sample, bins=bins, range=data_range, density=True)

        # Get locations of the histogram bins
        centers = (
            0.5 * (np.array(hist_data[1])[:, 1:] - np.array(hist_data[1])[:, :-1])
            + np.array(hist_data[1])[:, :-1]
        )
        xs = np.meshgrid(*centers)
        xs = np.array(xs).T.reshape(-1, dims)
        xt = np.meshgrid(*centers)
        xt = np.array(xt).T.reshape(-1, dims)
        M = ot.dist(xs, xt, metric="euclidean")
        A = hist_data[0].reshape(xs.shape[0])
        B = hist_sample[0].reshape(xt.shape[0])
        wasserstein = ot.emd2(A, B, M)

        if (wasserstein != wasserstein_last) and (wasserstein != 0):
            residue_rel = np.abs((wasserstein_last - wasserstein) / wasserstein)
        else:
            residue_rel = 0.0
        residue_abs = np.abs(wasserstein_last - wasserstein)
        distances.append(wasserstein)
        if (residue_rel < conv_rel) and (residue_abs < conv_abs):
            consecutive_counter += 1
        wasserstein_last = wasserstein
        iteration += 1

    n_sample = len(sample)
    n_data = len(data)
    if verbose:
        print(
            f"- Sample size reduction: {n_sample} / {n_data}"
            + f"\t({n_sample/n_data*100:.1f}%),"
            + f"\twasserstein = {wasserstein:.3g},"
            + f"\trel = {residue_rel:.2g},"
            + f"\tabs = {residue_abs:.2g}"
        )
    return sample, distances
