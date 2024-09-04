import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import scipy.interpolate as interp
from scipy.stats import chi2


# Find the bin centers
def centers(edges):
    return edges[:-1] + 0.5 * np.diff(edges[:2])


def np_hist_to_cv(counts):
    return counts.ravel().astype("float32")


def sample_single_dataset(filename):
    import cv2 as cv

    # Read the data
    df = pd.read_csv(filename)

    # Calculate log10 of G and V columns
    df["log10_G"] = np.log10(df["G"])
    df["log10_V"] = np.log10(df["V"])

    # Find the minimum and maximum values of the data
    min_G = df["log10_G"].min()
    max_G = df["log10_G"].max()
    min_V = df["log10_V"].min()
    max_V = df["log10_V"].max()

    def get_pdf_eval(df, nbins):
        # TODO: Update this to use function for n-dimensional data:
        # - https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.gaussian_kde.html
        # - https://pythonot.github.io/auto_examples/gromov/plot_gromov.html

        # Use numpy's histogram2d to calculate the 2D histogram
        H, xedges, yedges = np.histogram2d(
            df["log10_V"],
            df["log10_G"],
            bins=nbins,
            range=[[min_V, max_V], [min_G, max_G]],
            density=True,
        )

        xcenters = centers(xedges)
        ycenters = centers(yedges)

        # Interpolate the histogram
        pdf = interp.interp2d(xcenters, ycenters, H)
        pdf_eval = pdf(xedges, yedges)
        return pdf_eval

    # Sample the data until the limit is reached
    sf = 0
    sf0 = -1
    tol = 0.005
    n_samples = 100
    inc_samples = 100
    nbins = 25
    pdf_eval_ref = get_pdf_eval(df, nbins)
    sfs = []
    ns = []
    while (np.abs(sf - sf0) > tol) or (sf < 0.75):
        sf0 = sf

        # Sample the data and get evaluation of the PDF
        df_sample = df.sample(n=int(n_samples))
        pdf_eval = get_pdf_eval(df_sample, nbins)

        # Calculate the difference between the PDFs
        h1 = np_hist_to_cv(pdf_eval)
        h2 = np_hist_to_cv(pdf_eval_ref)
        dof = len(h1) - 1
        diff = cv.compareHist(h1, h2, cv.HISTCMP_CHISQR)
        sf = chi2.sf(diff, 1)
        ns.append(n_samples)
        sfs.append(sf * 100)
        n_samples += inc_samples

    # Plot the results
    fig, ax = plt.subplots()
    ax.plot(ns, sfs, "k-", zorder=2)
    ax.text(
        ns[-1],
        sfs[-1],
        f"N={ns[-1]}\n{sfs[-1]:.2f}%",
        horizontalalignment="right",
        verticalalignment="bottom",
    )

    # Continue with the calculation until sf >= 0.99 is reached
    inc_samples = 10000
    while sf < 0.99:
        sf0 = sf

        # Sample the data and get evaluation of the PDF
        df_sample = df.sample(n=int(n_samples))
        pdf_eval = get_pdf_eval(df_sample, nbins)

        # Calculate the difference between the PDFs
        h1 = np_hist_to_cv(pdf_eval)
        h2 = np_hist_to_cv(pdf_eval_ref)
        dof = len(h1) - 1
        diff = cv.compareHist(h1, h2, cv.HISTCMP_CHISQR)
        sf = chi2.sf(diff, 1)
        ns.append(n_samples)
        sfs.append(sf * 100)
        n_samples += inc_samples

    # Plot the results
    ax.plot(ns, sfs, "b--", zorder=1)
    ax.text(
        ns[-1],
        sfs[-1],
        f"N={ns[-1]}\n{sfs[-1]:.2f}%",
        horizontalalignment="right",
        verticalalignment="bottom",
    )

    # Set the plot parameters
    ax.set_xscale("log")
    ax.set_xlabel("Number of samples")
    ax.set_ylabel("Similarity factor (%)")
    plt.savefig("sample_single_dataset.png", dpi=300, bbox_inches="tight")
    plt.show()
