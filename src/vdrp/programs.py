from vdrp import utils
from vdrp.vdrp_helpers import run_command

import os
import shutil
import numpy as np


_vdrp_bindir = utils.bindir()


def call_imextsp(filename, ifuslot, wl, wlw, tpavg, norm, outfile):
    """
    Equivalent of the rextsp script,
    a wrapper around the imextsp fortran routine.

    Extracts the spectrum from the multi fits files and writes the tmp*dat.
    This also calculates the appropriate photon errors, using counting and
    sky residual errors. This applies the throughput and fiber to fiber.

    Parameters
    ----------
    filename : str
        The filename to process
    ifuslot : str
        The ifuslot name
    wl : float
        The central extraction wavelength
    wlw : float
        The width of the extraction window around wl
    tpavg : float
        Throughput average for the spectrum
    norm : float
        Fiber to fiber normaliztion for the spectrum
    outfile : str
        Name of the output filename
    """
    input = '"{filename:s}"\n{ifuslot} {wl} {wlw}\n"{tpavg}"\n"{norm}"\n'

    try:
        os.remove('out.sp')
    except OSError:
        pass

    try:
        os.remove(outfile)
    except OSError:
        pass

    s = input.format(filename=filename, ifuslot=ifuslot, wl=wl, wlw=wlw,
                     tpavg=tpavg, norm=norm)

    run_command(_vdrp_bindir + '/imextsp', s)

    shutil.move('out.sp', 'specin')

    run_command(_vdrp_bindir + '/specclean')

    shutil.move('out', outfile)


def call_sumsplines(nspec):
    """
    Call sumsplines, calculate a straight sum of the spectra in a list,
    including errors. Expects the spectra to be called tmp101 to
    tmp100+nspec.

    Creates a file called splines.out

    Parameters
    ----------
    nspec : int
        Number of spectra to read.
    """
    with open('list', 'w') as f:
        for i in range(0, nspec):
            f.write('tmp{c}.dat\n'.format(c=i+101))

    run_command(_vdrp_bindir + '/sumsplines')


def call_fitonevp(wave, outname):
    """
    Call fitonevp

    Requires fitghsp.in created by apply_factor_spline

    Parameters
    ----------
    wave : float
        Wavelength
    outname : str
        Output filename
    """
    input = '0 0\n{wave:f}\n/vcps\n'

    run_command(_vdrp_bindir + '/fitonevp', input.format(wave=wave))

    shutil.move('pgplot.ps', outname+'tot.ps')
    shutil.move('out', outname+'spec.dat')
    shutil.move('lines.out', outname+'spec.res')

    splinedata = np.loadtxt('splines.out')

    with open(outname+'spece.dat', 'w') as f:
        for d in splinedata:
            f.write('%.4f\t%.7f\t%.8e\t%.7f\t%.8e\n'
                    % (d[0], d[1], d[3], d[2]*1e17, d[4]*1e17))


def call_fit2d(ra, dec, outname):
    """
    Call fit2d. Calculate the 2D spatial fit based on fwhm, fiber locations,
    and ADC. This convolves the PSF over each fiber, for a given input
    position. It fits the ampltiude, minimizing to a chi^2.

    Requires input files generated by run_fit2d

    Parameters
    ----------
    ra : float
        Right Ascension of the star.
    dec : float
        Declination of the star.
    outname : str
        Output filename.
    """
    input = '{ra:f} {dec:f}\n/vcps\n'

    run_command(_vdrp_bindir + '/fit2d', input.format(ra=ra, dec=dec))

    shutil.move('pgplot.ps', outname)
    shutil.move('out', 'out2d')


def call_mkimage(ra, dec, starobs):
    """
    Call mkimage, equivalent of rmkim

    Reads the out2d file and creates three images of the
    emission line data, best fit model and residuals, called
    im[123].fits.

    Parameters
    ----------
    ra : float
        Right Ascension of the star.
    dec : float
        Declination of the star.
    starobs : list
        List of StarObservation objects for the star
    """

    gausa = np.loadtxt('out2d', ndmin=1, usecols=[9])

    # First write the first j4 input file
    with open('j4', 'w') as f:
        for obs in starobs:
            f.write('%f %f %f\n' % (3600.*(obs.ra-ra)
                                    * np.cos(dec/57.3),
                                    3600*(obs.dec-dec), obs.avg))

    run_command(_vdrp_bindir + '/mkimage')

    shutil.move('image.fits', 'im1.fits')

    with open('j4', 'w') as f:
        for i in range(0, len(starobs)):
            f.write('%f %f %f\n' % (3600.*(starobs[i].ra-ra)
                                    * np.cos(dec/57.3),
                                    3600*(starobs[i].dec-dec),
                    starobs[i].avg - gausa[i]))

    run_command(_vdrp_bindir + '/mkimage')

    shutil.move('image.fits', 'im2.fits')

    with open('j4', 'w') as f:
        for i in range(0, len(starobs)):
            f.write('%f %f %f\n' % (3600.*(starobs[i].ra-ra)
                                    * np.cos(dec/57.3),
                                    3600*(starobs[i].dec-dec),
                    gausa[i]))

    run_command(_vdrp_bindir + '/mkimage')

    shutil.move('image.fits', 'im3.fits')


def call_fitem(wl):
    """
    Call fitem requires input files created by run_fitem

    The line fitter. It fits a gauss-hermite. input is fitghsp.in.

    Parameters
    ----------
    wl : float
        Wavelength
    """

    input = '{wl:f}\n/vcps\n'

    run_command(_vdrp_bindir + '/fitem', input.format(wl=wl))


def call_sumspec(starname):
    """
    Call sumpspec. Sums a set of spectra, and then bins to 100AA bins.
    Used for SED fitting.

    Parameters
    ----------
    starname : str
        Star name used to create the outputn filename (adds specf.dat)
    """
    if os.path.exists('sumspec.out'):
        os.remove('sumspec.out')
    with open('list', 'w') as f:
        f.write(starname + 'specf.dat')

    run_command(_vdrp_bindir + '/sumspec')


def call_getnormexp(nightshot):
    """
    Call getnormexp. Get fwhm and relative normalizations for the frames.

    Parameters
    ----------
    name : str
        Observation name
    """
    input = '{name:s}\n'

    run_command(_vdrp_bindir + '/getnormexp', input.format(name=nightshot))


def run_fitradecsp(ra, dec, step, nstep, w_center, w_range, ifit1,
                   starobs, specfiles):
    """
    Setup and call fitradecsp. This creates a file called spec.out

    Parameters
    ----------
    starobs : list
        List of StarObservation structures one for each fiber
    specfiles : list
        List of filename of the different spec files
    """

    with open('list', 'w') as f:
        for st, sp in zip(starobs, specfiles):
            f.write('%s %.7f %.7f %.6f %s\n' % (sp, st.ra, st.dec,
                    st.structaz, st.expname))

    input = '{ra:.5f} {dec:.5f} {step:d} {nstep:d} {wcen:f} {wr:f} {ifit1:d}\n'

    run_command(_vdrp_bindir + '/fitradecsp',
                input.format(ra=ra, dec=dec, step=step, nstep=nstep,
                             wcen=w_center, wr=w_range, ifit1=ifit1))


def call_mkimage3d():
    """
    Run the mkimage3d command, creating an output file called image3d.fits
    """

    print(os.path.exists('./image3d.fits'))
    if os.path.exists('./image3d.fits'):
        os.remove('./image3d.fits')
    print(os.path.exists('./image3d.fits'))

    run_command(_vdrp_bindir + '/mkimage3d')
