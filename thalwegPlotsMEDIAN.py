# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 07:57:33 2024

@author: LawineNaturgefahren
"""

# -*- coding: utf-8 -*-
"""
script for creating thalweg analyse plots
"""

import pathlib

# local imports
import avaframe.in3Utils.geoTrans as gT
import avaframe.out3Plot.plotUtils as pU
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def plotBoxPlot(
    dbData,
    colList,
    outDir,
    namePlot,
    ylim=(0, 0),
    split="",
    renameTitle=[],
    renameY=[],
    renameX=[],
):
    """create a violin plot of colList from dbData

    Parameters
    -----------
    dbData: pandas dataframe
        dataframe with geometry info
    colList: list
        names of columns in dbData to plot
    outDir: pathlib path or str
        path to folder where plot shall be saved to
    namePlot: str
        name of plot to be added to boxplot
    ylim: tuple
        if specified range of y-axis
    split: string
        name of a column in dbData by which the data should be split
    renameTitle: array of stings
        if specified, individual names for plots
    renameY: array of stings
        if specified, individual names for yaxis
    --------------------------------------------

    return:
        path where the plot is saved

    """

    # if attribute which should be used for the split is defined
    if split != "":
        colPalette = ["#a1cfca", "#b8cc91", "#f3bd50", "#e17f6f"]

        # creats general plot size
        fig, axes = plt.subplots(1, len(colList), figsize=(10, 6))
        for i, col in enumerate(colList):
            # if only one column is provided, only one characteristic is analysed
            if len(colList) == 1:
                sn = sns.violinplot(
                    data=dbData[col], color="#a3a3a3", fill=False, cut=0
                )
                sn = sns.stripplot(
                    data=dbData[col],
                    jitter=True,
                    color="grey",
                    size=2,
                    zorder=1,
                    alpha=0.45,
                )
                sn = sns.violinplot(
                    data=dbData, x=split, y=col, palette=colPalette, fill=False, cut=0
                )
                sns.stripplot(
                    data=dbData,
                    x=split,
                    y=col,
                    jitter=True,
                    color="grey",
                    size=2,
                    zorder=1,
                    alpha=0.45,
                )
                # sns.set(style="darkgrid")
                axes.axvline(x=0.5, color="lightgrey", linestyle="--")
                # set y-axis
                if ylim != (0, 0):
                    sn.set(ylim=ylim)

                # calculate median for each boxplot, write it to the center of it
                means = dbData.groupby(split)[col].median()  # mean for each maxpotsize
                allmean = pd.Series(dbData[col].median())  # overall mean
                means = pd.concat([allmean, means])

                # calculate quantiles, if uncommented shown in plot
                quantileM = dbData.groupby(split)[col].quantile(0.75)
                quantileAll = np.quantile(pd.Series(dbData[col]), 0.75)
                quantileAll = pd.Series(quantileAll)
                quantile = pd.concat([quantileAll, quantileM])

                for xtick, (mean, quantil) in enumerate(zip(means, quantile)):

                    # plot median in the middel of boxplot
                    # axes[i].text(xtick, mean, f'{mean:.2f}\n{quantil:.2f}', ha='center', va='top', color='black', size=18)
                    axes.text(
                        xtick,
                        mean,
                        f"{mean:.1f}",
                        ha="center",
                        va="top",
                        color="black",
                        size=18,
                    )
                    # axes.text(xtick, quantil, f'{quantil:.1f}', ha='center', color='black', size=14)

                # calculate samplesize and number of nan's used for the boxplot, write it to the bottom of the plot
                samplesize = dbData.groupby(split)[col].count()
                fullsample = pd.Series(dbData[col].count())
                samplesize = pd.concat([fullsample, samplesize])

                totalcount = dbData[split].value_counts()
                totalcount = pd.DataFrame(totalcount).reset_index()
                totalcount.loc[len(totalcount)] = [0, dbData[col].count()]

                # print samplesize for each bin
                for xtick, group in enumerate(samplesize.index):

                    count = totalcount[totalcount[split] == group]["count"]
                    n = samplesize[group]
                    delet = int(count) - n
                    # axes.text(xtick, ylim[0], f'n={n}\ndel={delet}', ha='center', va='bottom', color='black', fontsize=8)
                    axes.text(
                        xtick,
                        ylim[0],
                        f"n={n}",
                        ha="center",
                        va="bottom",
                        color="black",
                        fontsize=15,
                    )

                if renameTitle == []:
                    axes.set_title(
                        "Distribution of Maxpotsize for %s" % col[0:20], loc="left"
                    )
                else:
                    axes.set_title(renameTitle[i], fontsize=22, loc="left")

                if renameY == []:
                    axes.set_ylabel("")
                else:
                    axes.set_ylabel(renameY[i], fontsize=20)
                    axes.tick_params(axis="both", labelsize=18)

                axes.set_facecolor("xkcd:white")
                axes.grid(linestyle="-", color="lightgrey", alpha=0.4, axis="y")
                # axes.set_xlabel(split, fontsize=18)
                axes.set_xlabel(r"$D_{max}$", fontsize=18)
                plt.subplots_adjust(left=0.15)
                # rect = Rectangle((0, 0), 1, 1, transform=fig.transFigure, color="darkgrey", fill=False, lw=1)
                # fig.patches.append(rect)

            # if multiple characteristic should be plotted next to each other
            else:
                # plots scatter, and violin plots
                sn = sns.violinplot(
                    data=dbData[col], ax=axes[i], color="#a3a3a3", fill=False, cut=0
                )
                sn = sns.stripplot(
                    data=dbData[col],
                    ax=axes[i],
                    jitter=True,
                    color="grey",
                    size=2,
                    zorder=1,
                    alpha=0.45,
                )
                sn = sns.violinplot(
                    data=dbData,
                    x=split,
                    y=col,
                    ax=axes[i],
                    palette=colPalette,
                    fill=False,
                    cut=0,
                )
                sns.stripplot(
                    data=dbData,
                    x=split,
                    y=col,
                    ax=axes[i],
                    jitter=True,
                    color="grey",
                    size=2,
                    zorder=1,
                    alpha=0.45,
                )
                # sns.set(style="darkgrid")
                axes[i].axvline(x=0.5, color="lightgrey", linestyle="--")

                # set y-axis
                if ylim != (0, 0):
                    sn.set(ylim=ylim)

                # calculate median for each boxplot, write it to the center of it
                means = dbData.groupby(split)[col].median()  # mean for each maxpotsize
                allmean = pd.Series(dbData[col].median())  # overall mean
                means = pd.concat([allmean, means])

                # adds median to plot
                for xtick, mean in enumerate(means):
                    # space = quantil-mean
                    # axes[i].text(xtick, mean, f'{mean:.2f}\n{quantil:.2f}', ha='center', va='top', color='black', size=18)
                    axes[i].text(
                        xtick,
                        mean,
                        f"{mean:.1f}",
                        ha="center",
                        va="top",
                        color="black",
                        size=18,
                    )
                    # axes[i].text(xtick, quantil, f'{quantil:.1f}', ha='center',  color='black', size=14)

                # calculate samplesize and number of nan's used for the boxplot, write it to the bottom of the plot
                samplesize = dbData.groupby(split)[col].count()
                fullsample = pd.Series(dbData[col].size)
                samplesize = pd.concat([fullsample, samplesize])

                totalcount = dbData[split].value_counts()
                totalcount = pd.DataFrame(totalcount).reset_index()
                totalcount.loc[len(totalcount)] = [0, dbData[col].count()]
                for xtick, group in enumerate(samplesize.index):

                    count = totalcount[totalcount[split] == group]["count"]
                    n = samplesize[group]
                    delet = int(count) - n
                    # axes[i].text(xtick, ylim[0], f'n={n}\ndel={delet}', ha='center', va='bottom', color='black', size=20)
                    axes[i].text(
                        xtick,
                        ylim[0],
                        f"n={n}",
                        ha="center",
                        va="bottom",
                        color="black",
                        size=12,
                    )

                # axes[i].set_xlabel( split )
                axes[i].set_ylabel(namePlot[:-1])
                if renameTitle == []:
                    axes[i].set_title(
                        "Distribution of Maxpotsize for %s" % col[0:20], loc="left"
                    )
                else:
                    # axes[i].set_title('')
                    axes[i].set_title(renameTitle[i], fontsize=22, loc="left")

                if renameY == []:
                    axes[i].set_ylabel(namePlot[:-1], fontsize=18)
                else:
                    axes[i].set_ylabel(renameY[i], fontsize=20)
                    axes[i].tick_params(axis="both", labelsize=18)
                axes[i].set_xlabel(split, fontsize=18)
                axes[i].set_facecolor("xkcd:white")
                axes[i].grid(linestyle="-", color="lightgrey", alpha=0.4, axis="y")
                # rect = Rectangle((0, 0), 1, 1, transform=fig.transFigure, color="darkgrey", fill=False, lw=1)
                # fig.patches.append(rect)

        # plot is sved
        outFile = "violinplots_%s_%s" % (namePlot, split)

    # if only one violin is plotted and not splitted by the split attribute
    else:
        colPalette = [
            "#a1cae2",
            "#0b3f5e",
            "#3b93ea",
            "#de6326",
            "#d17547",
            "#0fbddb",
            "#1c5761",
        ]
        fig = plt.figure(figsize=(6 * int(len(colList)), 8))
        ax3 = plt.subplot(111)
        sns.stripplot(
            data=dbData[colList], jitter=True, color="grey", alpha=0.5, size=2, zorder=1
        )
        sn = sns.violinplot(data=dbData[colList], palette=colPalette, fill=False, cut=0)

        if ylim != 0:
            sn.set(ylim=ylim)

        ax3.tick_params(labelsize=16)

        # calculation of statistical values, adds them to plot
        for idx, col in enumerate(colList):
            mean_value = dbData[col].median()
            quantile = dbData[col].quantile(0.75)
            x_position = idx
            ax3.text(
                x_position,
                mean_value,
                f"{mean_value:.1f}",
                ha="center",
                va="center",
                color="black",
                fontsize=22,
            )

        if renameTitle == []:
            ax3.set_title(
                "Distribution of %s for %d events"
                % (namePlot, len(dbData[colList[0]])),
                fontsize=20,
            )
        else:
            ax3.set_title(
                renameTitle[0] + " for %d events" % len(dbData[colList[0]]), fontsize=20
            )

        if renameY == []:
            ax3.set_ylabel(namePlot)
        else:
            ax3.set_ylabel(renameY[0], fontsize=20)

        if renameX == []:
            ax3.set_xlabel(namePlot)
        else:
            ax3.set_xticklabels(renameX, fontsize=16)

        # ax3.set_xlabel('thalwegs', fontsize = 20)
        sns.set(style="whitegrid")
        ax3.tick_params(axis="both", labelsize=20)
        outFile = "violinplots_%s" % namePlot
    # save figure
    plotPath = pU.saveAndOrPlot({"pathResult": outDir}, outFile, fig)

    return plotPath


def multiplePlots3(plist, name, title, outdir):
    """puts multiple plots next to each other and underneath each other,
    saves them as new plot and delets single plots"""

    nrows = 2
    ncols = 2

    # Create a figure with 2 rows and 2 columns
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(15, 10))
    fig.suptitle(title)

    # Loop over the plots and add them to the figure
    for i, plotpath in enumerate(plist):
        row = i // ncols  # Determine the row index
        col = i % ncols  # Determine the column index
        axes[row, col].imshow(plt.imread(plotpath))
        axes[row, col].axis("off")  # Hide the axes for better display

    for ax in axes.flatten():
        ax.grid(False)
        ax.set_facecolor("white")
        ax.set_axis_off()

    outFile = name
    pU.saveAndOrPlot({"pathResult": outdir}, outFile, fig)


def multiplePlots2(plist, name, title, outdir):
    """puts multiple plots next to each other, saves them as new plot and delets single plots"""
    fig, axes = plt.subplots(nrows=1, ncols=len(plist), figsize=(12, 6))
    # fig, axes = plt.subplots(nrows=1, ncols=len(plist), figsize=(len(plist)*3, len(plist)))
    fig.suptitle(title)

    for i, plotpath in enumerate(plist):
        axes[i].imshow(plt.imread(plotpath))

    for ax in axes.flatten():
        ax.grid(False)
        ax.set_facecolor("white")
        ax.set_axis_off()

    outFile = name
    pU.saveAndOrPlot({"pathResult": outdir}, outFile, fig)


def plotSlopeAngelAnalysis(
    db, avaPathLine, avaPathsz, pointList, cfg, pathList=[], name1=""
):
    """
    create x-y plot of thalweg using s(distances) and z-coordinates

    Parameters
    -----------
    db: pandas dataframe
        dataframe with data of geometries which should be plotted
    avaPathLine: string
        name of Thalweg column in db, with x,y,z coordinates
    avaPathzs: string
        name of Thalweg column in db, with s and z coordinates
    pointList: list of strings
        list with column names of points which should be plotted on thalweg
    cfg: configuration File
        information about: slope angles, resample distance, projection, working Dir
    pathList: list with strings
        list with column names of fitted paths
    name1: str
        name to be added to plate name to indicate what options are used


    """

    avalancheDir = pathlib.Path(cfg["MAIN"]["avalancheDir"])
    fitOption = cfg["FILTERING"]["fit"]

    # loop over all events in dbData
    for index, row in db.iterrows():
        avaPath = {
            "x": row[avaPathLine].xy[0],
            "y": row[avaPathLine].xy[1],
            "z": row[avaPathsz].xy[1],
            "s": row[avaPathsz].xy[0],
        }

        fig, axes = plt.subplots(figsize=(8, 5))
        if pathList != []:
            for path in pathList:
                if path == "curveFit_s_z":
                    label = "parabolic fit until: " + str(fitOption)
                    # label = r'fit: $a \cdot \exp(-b \cdot s^2) + c$'
                    # label = r'fit: $a \cdot \exp(-b \cdot s) + c$'
                    plt.plot(
                        row[path].xy[0],
                        row[path].xy[1],
                        label=label,
                        color="blue",
                        alpha=1,
                        lw=1,
                    )
                else:
                    plt.plot(row[path].xy[0], row[path].xy[1], "--", color="blue", lw=1)

        if "maxpotsize" in row:
            label = "thalweg maxpotsize: " + str(row["maxpotsize"])
        else:
            label = "full thalweg"
        plt.plot(avaPath["s"], avaPath["z"], "--", color="grey", label=label)
        plt.plot(
            avaPath["s"][int(row["origID"]) : int(row["depoID"])],
            avaPath["z"][int(row["origID"]) : int(row["depoID"])],
            label="thalweg section of interest",
            color="k",
            lw=1.5,
        )

        for point in pointList:

            if pd.notna(row[point]):
                pointDict = {"x": [row[point].x], "y": [row[point].y]}
                pointAvapath = gT.findClosestPoint(
                    avaPath["x"], avaPath["y"], pointDict
                )

                if "rel" in point:
                    legend = "release point"
                    # legend = 'depo γ(depo): ' +str(round(row['orig-depo_Angle'],2))
                    plt.plot(
                        avaPath["s"][pointAvapath],
                        avaPath["z"][pointAvapath],
                        "*",
                        markersize=10,
                        color="lightgrey",
                        label=legend,
                    )

                if "orig" in point:
                    legend = "O-point"
                    label = round(
                        row["geom_origin_pt3d_epsg:31287_snapped_gradient"], 2
                    )
                    plt.plot(
                        avaPath["s"][pointAvapath],
                        avaPath["z"][pointAvapath],
                        "c*",
                        markersize=10,
                        label=legend,
                    )
                    # plt.text(avaPath['s'][pointAvapath], avaPath['z'][pointAvapath], label, fontsize=7, va='top', ha='right')

                if "transit" in point:
                    legend = "T-point $\gamma_T:$" + str(
                        round(row["orig-transit_Angle"], 2)
                    )
                    # legend = 'transit point'
                    label = round(
                        row["geom_transit_pt3d_epsg:31287_snapped_gradient"], 2
                    )
                    plt.plot(
                        avaPath["s"][pointAvapath],
                        avaPath["z"][pointAvapath],
                        "g*",
                        markersize=10,
                        label=legend,
                    )
                    # plt.text(avaPath['s'][pointAvapath], avaPath['z'][pointAvapath], label, fontsize=7, va='top', ha='right')

                if "runout" in point:
                    label = round(
                        row["geom_runout_pt3d_epsg:31287_snapped_gradient"], 2
                    )
                    # legend = 'deposition point'
                    legend = r"D-point $\gamma_D =\beta:$" + str(
                        round(row["orig-depo_Angle"], 2)
                    )
                    plt.plot(
                        avaPath["s"][pointAvapath],
                        avaPath["z"][pointAvapath],
                        "*",
                        markersize=10,
                        color="#ad1d22",
                        label=legend,
                    )

                if "geom_event_pt3d" in point:
                    legend = r"R-point $\gamma_R =\alpha:$" + str(
                        round(row["orig-runout_Angle"], 2)
                    )
                    # legend = 'depo γ(depo): ' +str(round(row['orig-depo_Angle'],2))
                    plt.plot(
                        avaPath["s"][pointAvapath],
                        avaPath["z"][pointAvapath],
                        "*",
                        markersize=10,
                        color="grey",
                        label=legend,
                    )

        plt.xlabel(r"$s_{xy}$ [m]", fontsize=18)
        plt.ylabel(r"$z_s$ [m]", fontsize=18)
        plt.legend(facecolor="white", fontsize="large")
        plt.grid(color="lightgrey", linestyle="--")
        axes.set_facecolor("xkcd:white")
        axes.tick_params(axis="both", labelsize=16)

        outFile = "%s_%s_analysis_%s" % (row["path_name"], row["path_id"], name1)
        outFile = outFile.replace(" ", "")
        outFile = outFile.replace("/", "_")
        _ = pU.saveAndOrPlot({"pathResult": avalancheDir}, outFile, fig)
