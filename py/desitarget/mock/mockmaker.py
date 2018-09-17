# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
"""
=========================
desitarget.mock.mockmaker
=========================

Read mock catalogs and assign spectra.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import numpy as np
from glob import glob
from pkg_resources import resource_filename

import fitsio
import healpy as hp

from desimodel.io import load_pixweight
from desimodel import footprint
from desiutil.brick import Bricks
from desitarget.cuts import apply_cuts
from desisim.io import empty_metatable

from desiutil.log import get_logger, DEBUG
log = get_logger()

try:
    from scipy import constants
    C_LIGHT = constants.c/1000.0
except TypeError: # This can happen during documentation builds.
    C_LIGHT = 299792458.0/1000.0

def empty_targets_table(nobj=1):
    """Initialize an empty 'targets' table.

    Parameters
    ----------
    nobj : :class:`int`
        Number of objects.

    Returns
    -------
    targets : :class:`astropy.table.Table`
        Targets table.
    
    """
    from astropy.table import Table, Column
    
    targets = Table()

    targets.add_column(Column(name='RELEASE', length=nobj, dtype='i4'))
    targets.add_column(Column(name='BRICKID', length=nobj, dtype='i4'))
    targets.add_column(Column(name='BRICKNAME', length=nobj, dtype='U8'))
    targets.add_column(Column(name='BRICK_OBJID', length=nobj, dtype='i4'))
    targets.add_column(Column(name='TYPE', length=nobj, dtype='S4'))
    targets.add_column(Column(name='RA', length=nobj, dtype='f8', unit='degree'))
    targets.add_column(Column(name='DEC', length=nobj, dtype='f8', unit='degree'))
    targets.add_column(Column(name='RA_IVAR', length=nobj, dtype='f4', unit='1/degree^2'))
    targets.add_column(Column(name='DEC_IVAR', length=nobj, dtype='f4', unit='1/degree^2'))
    targets.add_column(Column(name='DCHISQ', length=nobj, dtype='f4', data=np.zeros( (nobj, 5) )))
    
    targets.add_column(Column(name='FLUX_G', length=nobj, dtype='f4', unit='nanomaggies'))
    targets.add_column(Column(name='FLUX_R', length=nobj, dtype='f4', unit='nanomaggies'))
    targets.add_column(Column(name='FLUX_Z', length=nobj, dtype='f4', unit='nanomaggies'))
    targets.add_column(Column(name='FLUX_W1', length=nobj, dtype='f4', unit='nanomaggies'))
    targets.add_column(Column(name='FLUX_W2', length=nobj, dtype='f4', unit='nanomaggies'))
    
    targets.add_column(Column(name='FLUX_IVAR_G', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    targets.add_column(Column(name='FLUX_IVAR_R', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    targets.add_column(Column(name='FLUX_IVAR_Z', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    targets.add_column(Column(name='FLUX_IVAR_W1', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    targets.add_column(Column(name='FLUX_IVAR_W2', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    
    targets.add_column(Column(name='MW_TRANSMISSION_G', length=nobj, dtype='f4'))
    targets.add_column(Column(name='MW_TRANSMISSION_R', length=nobj, dtype='f4'))
    targets.add_column(Column(name='MW_TRANSMISSION_Z', length=nobj, dtype='f4'))
    targets.add_column(Column(name='MW_TRANSMISSION_W1', length=nobj, dtype='f4'))
    targets.add_column(Column(name='MW_TRANSMISSION_W2', length=nobj, dtype='f4'))

    targets.add_column(Column(name='NOBS_G', length=nobj, dtype='i2'))
    targets.add_column(Column(name='NOBS_R', length=nobj, dtype='i2'))
    targets.add_column(Column(name='NOBS_Z', length=nobj, dtype='i2'))
    targets.add_column(Column(name='FRACFLUX_G', length=nobj, dtype='f4'))
    targets.add_column(Column(name='FRACFLUX_R', length=nobj, dtype='f4'))
    targets.add_column(Column(name='FRACFLUX_Z', length=nobj, dtype='f4'))
    targets.add_column(Column(name='FRACMASKED_G', length=nobj, dtype='f4'))
    targets.add_column(Column(name='FRACMASKED_R', length=nobj, dtype='f4'))
    targets.add_column(Column(name='FRACMASKED_Z', length=nobj, dtype='f4'))
    targets.add_column(Column(name='ALLMASK_G', length=nobj, dtype='f4'))
    targets.add_column(Column(name='ALLMASK_R', length=nobj, dtype='f4'))
    targets.add_column(Column(name='ALLMASK_Z', length=nobj, dtype='f4'))
    
    targets.add_column(Column(name='PSFDEPTH_G', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    targets.add_column(Column(name='PSFDEPTH_R', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    targets.add_column(Column(name='PSFDEPTH_Z', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    targets.add_column(Column(name='GALDEPTH_G', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    targets.add_column(Column(name='GALDEPTH_R', length=nobj, dtype='f4', unit='1/nanomaggies^2'))
    targets.add_column(Column(name='GALDEPTH_Z', length=nobj, dtype='f4', unit='1/nanomaggies^2'))

    targets.add_column(Column(name='FRACDEV', length=nobj, dtype='f4'))
    targets.add_column(Column(name='FRACDEV_IVAR', length=nobj, dtype='f4'))
    targets.add_column(Column(name='SHAPEDEV_R', length=nobj, dtype='f4', unit='arcsec'))
    targets.add_column(Column(name='SHAPEDEV_R_IVAR', length=nobj, dtype='f4', unit='1/arcsec^2'))
    targets.add_column(Column(name='SHAPEDEV_E1', length=nobj, dtype='f4'))
    targets.add_column(Column(name='SHAPEDEV_E1_IVAR', length=nobj, dtype='f4'))
    targets.add_column(Column(name='SHAPEDEV_E2', length=nobj, dtype='f4'))
    targets.add_column(Column(name='SHAPEDEV_E2_IVAR', length=nobj, dtype='f4'))
    targets.add_column(Column(name='SHAPEEXP_R', length=nobj, dtype='f4', unit='arcsec'))
    targets.add_column(Column(name='SHAPEEXP_R_IVAR', length=nobj, dtype='f4', unit='1/arcsec^2'))
    targets.add_column(Column(name='SHAPEEXP_E1', length=nobj, dtype='f4'))
    targets.add_column(Column(name='SHAPEEXP_E1_IVAR', length=nobj, dtype='f4'))
    targets.add_column(Column(name='SHAPEEXP_E2', length=nobj, dtype='f4'))
    targets.add_column(Column(name='SHAPEEXP_E2_IVAR', length=nobj, dtype='f4'))

    # Gaia columns
    targets.add_column(Column(name='REF_ID', data=np.repeat(-1, nobj).astype('int64'))) # default is -1
    targets.add_column(Column(name='GAIA_PHOT_G_MEAN_MAG', length=nobj, dtype='f4'))
    targets.add_column(Column(name='GAIA_PHOT_G_MEAN_FLUX_OVER_ERROR', length=nobj, dtype='f4'))
    targets.add_column(Column(name='GAIA_PHOT_BP_MEAN_MAG', length=nobj, dtype='f4'))
    targets.add_column(Column(name='GAIA_PHOT_BP_MEAN_FLUX_OVER_ERROR', length=nobj, dtype='f4'))
    targets.add_column(Column(name='GAIA_PHOT_RP_MEAN_MAG', length=nobj, dtype='f4'))    
    targets.add_column(Column(name='GAIA_PHOT_RP_MEAN_FLUX_OVER_ERROR', length=nobj, dtype='f4'))
    targets.add_column(Column(name='GAIA_ASTROMETRIC_EXCESS_NOISE', length=nobj, dtype='f4'))
    targets.add_column(Column(name='GAIA_DUPLICATED_SOURCE', length=nobj, dtype=bool)) # default is False
    targets.add_column(Column(name='PARALLAX', length=nobj, dtype='f4'))
    targets.add_column(Column(name='PARALLAX_IVAR', data=np.ones(nobj, dtype='f4'))) # default is unity
    targets.add_column(Column(name='PMRA', length=nobj, dtype='f4'))
    targets.add_column(Column(name='PMRA_IVAR', data=np.ones(nobj, dtype='f4'))) # default is unity
    targets.add_column(Column(name='PMDEC', length=nobj, dtype='f4'))
    targets.add_column(Column(name='PMDEC_IVAR', data=np.ones(nobj, dtype='f4'))) # default is unity

    targets.add_column(Column(name='BRIGHTSTARINBLOB', length=nobj, dtype=bool)) # default is False

    targets.add_column(Column(name='EBV', length=nobj, dtype='f4'))
    targets.add_column(Column(name='PHOTSYS', length=nobj, dtype='|S1'))
    targets.add_column(Column(name='TARGETID', length=nobj, dtype='int64'))
    targets.add_column(Column(name='DESI_TARGET', length=nobj, dtype='i8'))
    targets.add_column(Column(name='BGS_TARGET', length=nobj, dtype='i8'))
    targets.add_column(Column(name='MWS_TARGET', length=nobj, dtype='i8'))

    targets.add_column(Column(name='PRIORITY', length=nobj, dtype='i8'))
    targets.add_column(Column(name='SUBPRIORITY', length=nobj, dtype='f8'))
    targets.add_column(Column(name='NUMOBS', length=nobj, dtype='i8'))
    targets.add_column(Column(name='HPXPIXEL', length=nobj, dtype='i8'))

    return targets

def empty_truth_table(nobj=1, templatetype='', use_simqso=True):
    """Initialize an empty 'truth' table.

    Parameters
    ----------
    nobj : :class:`int`
        Number of objects.
    use_simqso : :class:`bool`, optional
        Initialize a SIMQSO-style objtruth table. Defaults to True.

    Returns
    -------
    truth : :class:`astropy.table.Table`
        Truth table.
    objtruth : :class:`astropy.table.Table`
        Objtype-specific truth table (if applicable).
    
    """
    from astropy.table import Table, Column
    
    truth = Table()
    truth.add_column(Column(name='TARGETID', length=nobj, dtype='int64'))
    truth.add_column(Column(name='MOCKID', length=nobj, dtype='int64'))
    truth.add_column(Column(name='CONTAM_TARGET', length=nobj, dtype='i8'))

    truth.add_column(Column(name='TRUEZ', length=nobj, dtype='f4', data=np.zeros(nobj)))
    truth.add_column(Column(name='TRUESPECTYPE', length=nobj, dtype='U10')) # GALAXY, QSO, STAR, etc.
    truth.add_column(Column(name='TEMPLATETYPE', length=nobj, dtype='U10')) # ELG, BGS, STAR, WD, etc.
    truth.add_column(Column(name='TEMPLATESUBTYPE', length=nobj, dtype='U10')) # DA, DB, etc.

    truth.add_column(Column(name='TEMPLATEID', length=nobj, dtype='i4', data=np.zeros(nobj)-1))
    truth.add_column(Column(name='SEED', length=nobj, dtype='int64', data=np.zeros(nobj)-1))
    truth.add_column(Column(name='MAG', length=nobj, dtype='f4', data=np.zeros(nobj), unit='mag'))
    truth.add_column(Column(name='MAGFILTER', length=nobj, dtype='U15')) # normalization filter

    truth.add_column(Column(name='FLUX_G', length=nobj, dtype='f4', unit='nanomaggies'))
    truth.add_column(Column(name='FLUX_R', length=nobj, dtype='f4', unit='nanomaggies'))
    truth.add_column(Column(name='FLUX_Z', length=nobj, dtype='f4', unit='nanomaggies'))
    truth.add_column(Column(name='FLUX_W1', length=nobj, dtype='f4', unit='nanomaggies'))
    truth.add_column(Column(name='FLUX_W2', length=nobj, dtype='f4', unit='nanomaggies'))

    _, objtruth = empty_metatable(nmodel=nobj, objtype=templatetype, simqso=use_simqso)
    if len(objtruth) == 0:
        objtruth = [] # need an empty list for the multiprocessing in build.select_targets
    else:
        if (templatetype == 'QSO' or templatetype == 'ELG' or
            templatetype == 'LRG' or templatetype == 'BGS'):
            objtruth.add_column(Column(name='TRUEZ_NORSD', length=nobj, dtype='f4'))

    return truth, objtruth

def _get_radec(mockfile, nside, pixmap, mxxl=False):

    log.info('Reading {}'.format(mockfile))
    radec = fitsio.read(mockfile, columns=['RA', 'DEC'], upper=True, ext=1)
    ra = radec['RA'].astype('f8') % 360.0 # enforce 0 < ra < 360
    dec = radec['DEC'].astype('f8')

    log.info('Assigning healpix pixels with nside = {}.'.format(nside))
    allpix = footprint.radec2pix(nside, ra, dec)

    pixweight = load_pixweight(nside, pixmap=pixmap)

    return ra, dec, allpix, pixweight
        
def _default_wave(wavemin=None, wavemax=None, dw=0.2):
    """Generate a default wavelength vector for the output spectra."""
    from desimodel.io import load_throughput
    
    if wavemin is None:
        wavemin = load_throughput('b').wavemin - 10.0
    if wavemax is None:
        wavemax = load_throughput('z').wavemax + 10.0
            
    return np.arange(round(wavemin, 1), wavemax, dw)

class SelectTargets(object):
    """Methods to help select various target types.

    Parameters
    ----------
    bricksize : :class:`float`, optional
        Brick diameter used in the imaging surveys; needed to assign a brickname
        and brickid to each object.  Defaults to 0.25 deg.

    """
    GMM_LRG, GMM_ELG, GMM_BGS, GMM_QSO = None, None, None, None

    def __init__(self, bricksize=0.25):
        from astropy.io import fits
        from desiutil.dust import SFDMap
        from ..targetmask import desi_mask, bgs_mask, mws_mask
        from ..contammask import contam_mask
        
        self.desi_mask = desi_mask
        self.bgs_mask = bgs_mask
        self.mws_mask = mws_mask
        self.contam_mask = contam_mask

        self.Bricks = Bricks(bricksize=bricksize)
        self.SFDMap = SFDMap()

        # Read and cache the default pixel weight map.
        pixfile = os.path.join(os.environ['DESIMODEL'],'data','footprint','desi-healpix-weights.fits')
        with fits.open(pixfile) as hdulist:
            self.pixmap = hdulist[0].data

    def mw_transmission(self, data):
        """Compute the grzW1W2 Galactic transmission for every object.

        Parameters
        ----------
        data : :class:`dict`
            Input dictionary of sources with RA, Dec coordinates, modified on output
            to contain reddening and the MW transmission in various bands.
        params : :class:`dict`
            Dictionary summary of the input configuration file, restricted to a
            particular source_name (e.g., 'QSO').

        Raises
        ------

        """
        extcoeff = dict(G = 3.214, R = 2.165, Z = 1.221, W1 = 0.184, W2 = 0.113)
        data['EBV'] = self.SFDMap.ebv(data['RA'], data['DEC'], scaling=1.0)

        for band in ('G', 'R', 'Z', 'W1', 'W2'):
            data['MW_TRANSMISSION_{}'.format(band)] = 10**(-0.4 * extcoeff[band] * data['EBV'])

    def imaging_depth(self, data):
        """Add the imaging depth to the data dictionary.

        Note: In future, this should be a much more sophisticated model based on the
        actual imaging data releases (e.g., it should depend on healpixel).

        Parameters
        ----------
        data : :class:`dict`
            Input dictionary of sources with RA, Dec coordinates, modified on output
            to contain the PSF and galaxy depth in various bands.

        """
        nobj = len(data['RA'])

        psfdepth_mag = np.array((24.65, 23.61, 22.84)) # 5-sigma, mag
        galdepth_mag = np.array((24.7, 23.9, 23.0))    # 5-sigma, mag

        psfdepth_ivar = (1 / 10**(-0.4 * (psfdepth_mag - 22.5)))**2 # 5-sigma, 1/nanomaggies**2
        galdepth_ivar = (1 / 10**(-0.4 * (galdepth_mag - 22.5)))**2 # 5-sigma, 1/nanomaggies**2

        for ii, band in enumerate(('G', 'R', 'Z')):
            data['PSFDEPTH_{}'.format(band)] = np.repeat(psfdepth_ivar[ii], nobj)
            data['GALDEPTH_{}'.format(band)] = np.repeat(galdepth_ivar[ii], nobj)

        wisedepth_mag = np.array((22.3, 23.8)) # 1-sigma, mag
        wisedepth_ivar = 1 / (5 * 10**(-0.4 * (wisedepth_mag - 22.5)))**2 # 5-sigma, 1/nanomaggies**2

        for ii, band in enumerate(('W1', 'W2')):
            data['PSFDEPTH_{}'.format(band)] = np.repeat(wisedepth_ivar[ii], nobj)

    def scatter_photometry(self, data, truth, targets, indx=None, psf=True,
                           seed=None, qaplot=False):
        """Add noise to the input (noiseless) photometry based on the depth (as well as
        the inverse variance fluxes in GRZW1W2).

        The input targets table is modified in place.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        indx : :class:`numpy.ndarray`, optional
            Scatter the photometry of a subset of the objects in the data
            dictionary, as specified using their zero-indexed indices.
        psf : :class:`bool`, optional
            For point sources (e.g., QSO, STAR) use the PSFDEPTH values,
            otherwise use GALDEPTH.  Defaults to True.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        qaplot : :class:`bool`, optional
            Generate a QA plot for debugging.

        """
        if seed is None:
            seed = self.seed
        rand = np.random.RandomState(seed)
            
        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        if psf:
            depthprefix = 'PSF'
        else:
            depthprefix = 'GAL'

        factor = 5 # -- should this be 1 or 5???

        for band in ('G', 'R', 'Z'):
            fluxkey = 'FLUX_{}'.format(band)
            ivarkey = 'FLUX_IVAR_{}'.format(band)
            depthkey = '{}DEPTH_{}'.format(depthprefix, band)

            sigma = 1 / np.sqrt(data[depthkey][indx]) / 5 # nanomaggies, 1-sigma
            targets[fluxkey][:] = truth[fluxkey] + rand.normal(scale=sigma)

            targets[ivarkey][:] = 1 / sigma**2

        for band in ('W1', 'W2'):
            fluxkey = 'FLUX_{}'.format(band)
            ivarkey = 'FLUX_IVAR_{}'.format(band)
            depthkey = 'PSFDEPTH_{}'.format(band)

            sigma = 1 / np.sqrt(data[depthkey][indx]) / 5 # nanomaggies, 1-sigma
            targets[fluxkey][:] = truth[fluxkey] + rand.normal(scale=sigma)

            targets[ivarkey][:] = 1 / sigma**2

        if qaplot:
            self._qaplot_scatter_photometry(targets, truth)

    def _qaplot_scatter_photometry(self, targets, truth):
        """Build a simple QAplot, useful for debugging """
        import matplotlib.pyplot as plt

        gr1 = -2.5 * np.log10( truth['FLUX_G'] / truth['FLUX_R'] )
        rz1 = -2.5 * np.log10( truth['FLUX_R'] / truth['FLUX_Z'] )
        gr = -2.5 * np.log10( targets['FLUX_G'] / targets['FLUX_R'] )
        rz = -2.5 * np.log10( targets['FLUX_R'] / targets['FLUX_Z'] )
        plt.scatter(rz1, gr1, color='red', alpha=0.5, edgecolor='none', 
                    label='Noiseless Photometry')
        plt.scatter(rz, gr, alpha=0.5, color='green', edgecolor='none',
                    label='Noisy Photometry')
        plt.xlim(-0.5, 2) ; plt.ylim(-0.5, 2)
        plt.legend(loc='upper left')
        plt.show()

    def _sample_vdisp(self, ra, dec, mean=1.9, sigma=0.15, fracvdisp=(0.1, 1),
                      seed=None, nside=128):
        """Assign velocity dispersions to a subset of objects."""
        rand = np.random.RandomState(seed)

        def _sample(nmodel=1):
            nvdisp = int(np.max( ( np.min( ( np.round(nmodel * fracvdisp[0]), fracvdisp[1] ) ), 1 ) ))
            vvdisp = 10**rand.normal(loc=mean, scale=sigma, size=nvdisp)
            return rand.choice(vvdisp, nmodel)

        # Hack! Assign the same velocity dispersion to galaxies in the same
        # healpixel.
        nobj = len(ra)
        vdisp = np.zeros(nobj)

        healpix = footprint.radec2pix(nside, ra, dec)
        for pix in set(healpix):
            these = np.in1d(healpix, pix)
            vdisp[these] = _sample(nmodel=np.count_nonzero(these))

        return vdisp

    def read_GMM(self, target=None):
        """Read the GMM for the full range of morphological types of a given target
        type, as well as the magnitude-dependent morphological fraction.

        See desitarget/doc/nb/gmm-dr7.ipynb for details.

        """
        from astropy.io import fits
        from astropy.table import Table
        from desiutil.sklearn import GaussianMixtureModel

        if target is not None:
            try:
                if getattr(self, 'GMM_{}'.format(target.upper())) is not None:
                    return
            except:
                return

            gmmdir = resource_filename('desitarget', 'mock/data/dr7.1')
            if not os.path.isdir:
                log.warning('DR7.1 GMM directory {} not found!'.format(gmmdir))
                raise IOError
            
            fracfile = os.path.join(gmmdir, 'fractype_{}.fits'.format(target.lower()))
            fractype = Table.read(fracfile)

            gmm = []
            for morph in ('PSF', 'REX', 'EXP', 'DEV', 'COMP'):
                gmmfile = os.path.join(gmmdir, 'gmm_{}_{}.fits'.format(target.lower(), morph.lower()))
                if os.path.isfile(gmmfile): # not all targets have all morphologies
                    # Get the GMM properties modeled.
                    cols = []
                    with fits.open(gmmfile, 'readonly') as ff:
                        ncol = ff[0].header['NCOL']
                        for ii in range(ncol):
                            cols.append(ff[0].header['COL{:02d}'.format(ii)])
                    gmm.append( (morph, cols, GaussianMixtureModel.load(gmmfile)) )

            # Now unpack the list of tuples into a more convenient set of
            # variables and then repack and return.
            morph = [info[0] for info in gmm]
            gmmcols = [info[1] for info in gmm]
            GMM = [info[2] for info in gmm]

            setattr(SelectTargets, 'GMM_{}'.format(target.upper()), (morph, fractype, gmmcols, GMM))

    def sample_GMM(self, nobj, isouth=None, target=None, seed=None,
                   prior_mag=None, prior_redshift=None):
        """Sample from the GMMs read by self.read_GMM.

        See desitarget/doc/nb/gmm-dr7.ipynb for details.

        """
        rand = np.random.RandomState(seed)
        
        try:
            GMM = getattr(self, 'GMM_{}'.format(target.upper()))
            if GMM is None:
                self.read_GMM(target=target)
                GMM = getattr(self, 'GMM_{}'.format(target.upper()))
        except:
            return None # no GMM for this target
            
        morph = GMM[0]
        if isouth is None:
            isouth = np.ones(nobj).astype(bool)

        # Marginalize the morphological fractions over magnitude.
        magbins = GMM[1]['MAG'].data
        deltam = np.diff(magbins)[0]
        minmag, maxmag = magbins.min()-deltam / 2, magbins.max()+deltam / 2

        # Get the total number of each morphological type, accounting for
        # rounding.
        frac2d_magbins = np.vstack( [GMM[1][mm].data for mm in morph] )
        norm = np.sum(frac2d_magbins, axis=1)
        frac1d_morph = norm / np.sum(norm)
        nobj_morph = np.round(frac1d_morph*nobj).astype(int)
        dn = np.sum(nobj_morph) - nobj
        if dn > 0:
            nobj_morph[np.argmax(nobj_morph)] -= dn
        elif dn < 0:
            nobj_morph[np.argmax(nobj_morph)] += dn

        # Next, sample from the GMM for each morphological type.  For
        # simplicity we ignore the north-south split here.
        gmmout = {'MAGFILTER': np.zeros(nobj).astype('U15'), 'TYPE': np.zeros(nobj).astype('U4')}
        for key in ('MAG', 'FRACDEV', 'FRACDEV_IVAR',
                    'SHAPEDEV_R', 'SHAPEDEV_R_IVAR', 'SHAPEDEV_E1', 'SHAPEDEV_E1_IVAR', 'SHAPEDEV_E2', 'SHAPEDEV_E2_IVAR',
                    'SHAPEEXP_R', 'SHAPEEXP_R_IVAR', 'SHAPEEXP_E1', 'SHAPEEXP_E1_IVAR', 'SHAPEEXP_E2', 'SHAPEEXP_E2_IVAR',
                    'GR', 'RZ'):
            gmmout[key] = np.zeros(nobj).astype('f4')

        for ii, mm in enumerate(morph):
            if nobj_morph[ii] > 0:
                cols = GMM[2][ii]
                samp = np.empty( nobj, dtype=np.dtype( [(tt, 'f4') for tt in cols] ) )
                _samp = GMM[3][ii].sample(nobj)
                for jj, tt in enumerate(cols):
                    samp[tt] = _samp[:, jj]

                # Choose samples with the appropriate magnitude-dependent
                # probability, for this morphological type.
                prob = np.interp(samp[cols[0]], magbins, frac2d_magbins[ii, :])
                prob /= np.sum(prob)
                these = rand.choice(nobj, size=nobj_morph[ii], p=prob, replace=False)

                gthese = np.arange(nobj_morph[ii]) + np.sum(nobj_morph[:ii])

                if 'z' in samp.dtype.names:
                    gmmout['MAG'][gthese] = samp['z'][these]
                else:
                    gmmout['MAG'][gthese] = samp['r'][these]
                gmmout['GR'][gthese] = samp['gr'][these]
                gmmout['RZ'][gthese] = samp['rz'][these]
                gmmout['TYPE'][gthese] = np.repeat(mm, nobj_morph[ii])

                for col in ('reff', 'e1', 'e2'):
                    sampcol = '{}_{}'.format(col, mm.lower()) # e.g., reff_dev
                    sampsnrcol = 'snr_{}'.format(sampcol)     # e.g., snr_reff_dev

                    outcol = 'shape{}_{}'.format(mm.lower().replace('rex', 'exp'), col.replace('reff', 'r')).upper()
                    outivarcol = '{}_ivar'.format(outcol).upper()
                    if sampcol in samp.dtype.names:
                        val = samp[sampcol][these]
                        if col == 'reff':
                            val = 10**val
                        gmmout[outcol][gthese] = val
                        gmmout[outivarcol][gthese] = (10**samp[sampsnrcol][these] / val)**2 # S/N-->ivar

                if mm == 'DEV':
                    gmmout['FRACDEV'][:] = 1.0
                elif mm == 'EXP':
                    gmmout['FRACDEV'][:] = 0.0

        gmmout['FRACDEV'][gmmout['FRACDEV'] < 0.0] = 0.0
        gmmout['FRACDEV'][gmmout['FRACDEV'] > 1.0] = 1.0

        if target == 'LRG':
            band = 'z'
        else:
            band = 'r'

        # Sort based on the input/prior magnitude (e.g., for the BGS/MXXL
        # mocks), but note that we will very likely end up with duplicated
        # morphologies and colors.
        if prior_mag is not None:
            dmcut = 0.3
            srt = np.zeros(nobj).astype(int)
            for ii, mg in enumerate(prior_mag):
                dm = np.where( (np.abs(mg-gmmout['MAG']) < dmcut) )[0]
                if len(dm) == 0:
                    srt[ii] = np.argmin(np.abs(mg-gmmout['MAG']))
                else:
                    srt[ii] = rand.choice(dm)
            for key in gmmout.keys():
                gmmout[key][:] = gmmout[key][srt]

        # Shuffle based on input/prior redshift, so we can get a broad
        # correlation between magnitude and redshift.
        if prior_redshift is not None:
            pass
            #dat = np.zeros(nobj, dtype=[('redshift', 'f4'), ('mag', 'f4')])
            #dat['redshift'] = prior_redshift
            #dat['mag'] = gmmout['MAG']
            #srt = np.argsort(dat, order=('redshift', 'mag'))

        # Assign filter names.
        if np.sum(isouth) > 0:
            if target == 'LRG':
                gmmout['MAGFILTER'][isouth] = np.repeat('decam2014-z', np.sum(isouth))
            else:
                gmmout['MAGFILTER'][isouth] = np.repeat('decam2014-r', np.sum(isouth))

        if np.sum(~isouth) > 0:
            if target == 'LRG':
                gmmout['MAGFILTER'][~isouth] = np.repeat('MzLS-z', np.sum(~isouth))
            else:
                gmmout['MAGFILTER'][~isouth] = np.repeat('BASS-r', np.sum(~isouth))

        return gmmout

    def _query(self, matrix, subtype='', return_dist=False, south=True):
        """Return the nearest template number based on the KD Tree."""

        if subtype == '':
            try:
                dist, indx = self.tree.query(matrix) # no north-south split (e.g., BGS/MXXL)
            except:
                if south:
                    dist, indx = self.tree_south.query(matrix)
                else:
                    dist, indx = self.tree_north.query(matrix)
        else:
            if subtype.upper() == 'DA':
                dist, indx = self.tree_da.query(matrix)
            elif subtype.upper() == 'DB':
                dist, indx = self.tree_db.query(matrix)
            else:
                log.warning('Unrecognized SUBTYPE {}!'.format(subtype))
                raise ValueError

        if return_dist:
            return dist, indx.astype('i4')
        else:
            return indx.astype('i4')
        
    def sample_gmm_nospectra(self, meta, rand=None):
        """Sample from one of the Gaussian mixture models generated by
        desitarget/doc/nb/gmm-quicksurvey.ipynb.

        Note: Any changes to the quantities fitted in that notebook need to be
        updated here!
        
        """
        if rand is None:
            rand = np.random.RandomState()

        nsample = len(meta)
        target = meta['OBJTYPE'][0].upper()
        
        data = self.GMM_nospectra.sample(nsample, random_state=rand)

        alltags = dict()
        alltags['ELG'] = ('r', 'g - r', 'r - z', 'z - W1', 'W1 - W2', 'oii')
        alltags['LRG'] = ('z', 'g - r', 'r - z', 'z - W1', 'W1 - W2')
        alltags['BGS'] = ('r', 'g - r', 'r - z', 'z - W1', 'W1 - W2')
        alltags['QSO'] = ('g', 'g - r', 'r - z', 'z - W1', 'W1 - W2')
        alltags['LYA'] = ('g', 'g - r', 'r - z', 'z - W1', 'W1 - W2')

        tags = alltags[target]
        sample = np.empty( nsample, dtype=np.dtype( [(tt, 'f4') for tt in tags] ) )
        for ii, tt in enumerate(tags):
            sample[tt] = data[:, ii]

        if target == 'ELG' or target == 'BGS':
            rmag = sample['r']
            zmag = rmag - sample['r - z']
            gmag = sample['g - r'] + rmag
            normmag = rmag
        elif target == 'LRG':
            zmag = sample['z']
            rmag = sample['r - z'] + zmag
            gmag = sample['g - r'] + rmag
            normmag = zmag
        elif target == 'QSO' or target == 'LYA':
            gmag = sample['g']
            rmag = gmag - sample['g - r']
            zmag = rmag - sample['r - z']
            normmag = gmag

        W1mag = zmag - sample['z - W1'] 
        W2mag = W1mag - sample['W1 - W2'] 
        
        meta['MAG'][:] = normmag
        meta['FLUX_G'][:] = 1e9 * 10**(-0.4 * gmag)
        meta['FLUX_R'][:] = 1e9 * 10**(-0.4 * rmag)
        meta['FLUX_Z'][:] = 1e9 * 10**(-0.4 * zmag)
        meta['FLUX_W1'][:] = 1e9 * 10**(-0.4 * W1mag)
        meta['FLUX_W2'][:] = 1e9 * 10**(-0.4 * W2mag)

        return meta

    def deredden(self, targets):
        """Correct photometry for Galactic extinction."""

        unredflux = list()
        for band in ('G', 'R', 'Z', 'W1', 'W2'):
            unredflux.append(targets['FLUX_{}'.format(band)] /
                             targets['MW_TRANSMISSION_{}'.format(band)])
        gflux, rflux, zflux, w1flux, w2flux = unredflux

        return gflux, rflux, zflux, w1flux, w2flux

    def populate_targets_truth(self, data, meta, objmeta, indx=None, seed=None, psf=True,
                               use_simqso=True, truespectype='', templatetype='',
                               templatesubtype=''):
        """Initialize and populate the targets and truth tables given a dictionary of
        source properties and a spectral metadata table.  

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        indx : :class:`numpy.ndarray`, optional
            Populate the tables of a subset of the objects in the data
            dictionary, as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        psf : :class:`bool`, optional
            For point sources (e.g., QSO, STAR) use the PSFDEPTH values,
            otherwise use GALDEPTH.  Defaults to True.
        use_simqso : :class:`bool`, optional
            Initialize a SIMQSO-style objtruth table. Defaults to True.
        truespectype : :class:`str` or :class:`numpy.array`, optional
            True spectral type.  Defaults to ''.
        templatetype : :class:`str` or :class:`numpy.array`, optional
            True template type.  Defaults to ''.
        templatesubtype : :class:`str` or :class:`numpy.array`, optional
            True template subtype.  Defaults to ''.
        
        Returns
        -------
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        objtruth : :class:`astropy.table.Table`
            Corresponding objtype-specific truth table (if applicable).

        """
        if seed is None:
            seed = self.seed
            
        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        # Initialize the tables.
        targets = empty_targets_table(nobj)
        truth, objtruth = empty_truth_table(nobj, templatetype=templatetype,
                                            use_simqso=use_simqso)

        truth['MOCKID'][:] = data['MOCKID'][indx]
        if len(objtruth) > 0:
            if 'Z_NORSD' in data.keys() and 'TRUEZ_NORSD' in objtruth.colnames:
                objtruth['TRUEZ_NORSD'][:] = data['Z_NORSD'][indx]

        # Copy all information from DATA to TARGETS.
        for key in data.keys():
            if key in targets.colnames:
                if isinstance(data[key], np.ndarray):
                    targets[key][:] = data[key][indx]
                else:
                    targets[key][:] = np.repeat(data[key], nobj)

        # Assign RELEASE, PHOTSYS, [RA,DEC]_IVAR, and DCHISQ
        targets['RELEASE'][:] = 9999
        
        south = self.is_south(targets['DEC'])
        north = ~south
        if np.sum(south) > 0:
            targets['PHOTSYS'][south] = 'S'
        if np.sum(north) > 0:
            targets['PHOTSYS'][north] = 'N'
            
        targets['RA_IVAR'][:], targets['DEC_IVAR'][:] = 1e8, 1e8
        targets['DCHISQ'][:] = np.tile( [0.0, 100, 200, 300, 400], (nobj, 1)) # for QSO selection

        # Add dust, depth, and nobs.
        for band in ('G', 'R', 'Z', 'W1', 'W2'):
            key = 'MW_TRANSMISSION_{}'.format(band)
            targets[key][:] = data[key][indx]

        for band in ('G', 'R', 'Z'):
            for prefix in ('PSF', 'GAL'):
                key = '{}DEPTH_{}'.format(prefix, band)
                targets[key][:] = data[key][indx]
            nobskey = 'NOBS_{}'.format(band)
            targets[nobskey][:] = 2 # assume constant!

        #for band in ('W1', 'W2'):
        #    key = 'PSFDEPTH_{}'.format(band)
        #    targets[key][:] = data[key][indx]

        # Add spectral / template type and subtype.
        for value, key in zip( (truespectype, templatetype, templatesubtype),
                               ('TRUESPECTYPE', 'TEMPLATETYPE', 'TEMPLATESUBTYPE') ):
            if isinstance(value, np.ndarray):
                truth[key][:] = value
            else:
                truth[key][:] = np.repeat(value, nobj)

        # Copy various quantities from the metadata table.
        for key in meta.colnames:
            if key in truth.colnames:
                truth[key][:] = meta[key]
            elif key == 'REDSHIFT':
                truth['TRUEZ'][:] = meta['REDSHIFT']

        if len(objmeta) > 0 and len(objtruth) > 0: # some objects have no metadata...
            for key in objmeta.colnames:
                if key in objtruth.colnames:
                    objtruth[key][:] = objmeta[key]
            
        # Scatter the photometry based on the depth.
        self.scatter_photometry(data, truth, targets, indx=indx, psf=psf, seed=seed)

        # Finally, attenuate the observed photometry for Galactic extinction.
        for band, key in zip( ('G', 'R', 'Z', 'W1', 'W2'),
                              ('FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2') ):
            targets[key][:] = targets[key] * data['MW_TRANSMISSION_{}'.format(band)][indx]

        return targets, truth, objtruth

    def mock_density(self, mockfile=None, nside=16, density_per_pixel=False):
        """Compute the median density of targets in the full mock. 

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog.
        nside : :class:`int`
            Healpixel nside for the calculation.
        density_per_pixel : :class:`bool`, optional
            Return the density per healpixel rather than just the median
            density, which may be useful for statistical purposes.

        Returns
        -------
        mock_density : :class:`int` or :class:`numpy.ndarray`
            Median density of targets per deg2 or target density in all
            healpixels (if density_per_pixel=True).  

        Raises
        ------
        ValueError
            If mockfile is not defined.

        """
        if mockfile is None:
            log.warning('Mockfile input is required.')
            raise ValueError

        try:
            mockfile = mockfile.format(**os.environ)
        except KeyError as e:
            log.warning('Environment variable not set for mockfile: {}'.format(e))
            raise ValueError
        
        areaperpix = hp.nside2pixarea(nside, degrees=True)

        radec = fitsio.read(mockfile, columns=['RA', 'DEC'], upper=True, ext=1)
        healpix = footprint.radec2pix(nside, radec['RA'], radec['DEC'])

        # Get the weight per pixel, protecting against divide-by-zero.
        pixweight = load_pixweight(nside, pixmap=self.pixmap)
        weight = np.zeros_like(radec['RA'])
        good = np.nonzero(pixweight[healpix])
        weight[good] = 1 / pixweight[healpix[good]]

        mock_density = np.bincount(healpix, weights=weight) / areaperpix # [targets/deg]
        mock_density = mock_density[np.flatnonzero(mock_density)]

        if density_per_pixel:
            return mock_density
        else:
            return np.median(mock_density)

    def qamock_sky(self, data, xlim=(0, 4), nozhist=False, png=None):
        """Generate a QAplot showing the sky and redshift distribution of the objects in
        the mock.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.

        """
        import warnings
        import matplotlib.pyplot as plt
        from desiutil.plots import init_sky, plot_sky_binned
        
        fig, ax = plt.subplots(1, 2, figsize=(12, 4))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            basemap = init_sky(galactic_plane_color='k', ax=ax[0]);
            plot_sky_binned(data['RA'], data['DEC'], weights=data['WEIGHT'],
                            max_bin_area=hp.nside2pixarea(data['NSIDE'], degrees=True),
                            verbose=False, clip_lo='!1', clip_hi='98%', 
                            cmap='viridis', plot_type='healpix', basemap=basemap,
                            label=r'{} (targets/deg$^2$)'.format(self.objtype))
            
        if not nozhist:
            ax[1].hist(data['Z'], bins=100, histtype='stepfilled',
                       alpha=0.6, label=self.objtype, weights=data['WEIGHT'])
            ax[1].set_xlabel('Redshift')
            ax[1].set_xlim( xlim )
            ax[1].yaxis.set_major_formatter(plt.NullFormatter())
            ax[1].legend(loc='upper right', frameon=False)
        else:
            ax[1].axis('off')
        fig.subplots_adjust(wspace=0.2)

        if png:
            print('Writing {}'.format(png))
            fig.savefig(png)
            plt.close(fig)
        else:
            plt.show()

    def is_south(self, dec):
        """Divide the "north" and "south" photometric systems based on a
        constant-declination cut.

        Parameters
        ----------
        dec : :class:`numpy.ndarray`
            Declination of candidate targets (decimal degrees). 

        """
        return dec <= 32.125

class ReadGaussianField(SelectTargets):
    """Read a Gaussian random field style mock catalog."""
    cached_radec = None
    
    def __init__(self, **kwargs):
        super(ReadGaussianField, self).__init__(**kwargs)
        
    def readmock(self, mockfile=None, healpixels=None, nside=None,
                 zmax_qso=None, target_name='', mock_density=False,
                 seed=None):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        zmax_qso : :class:`float`
            Maximum redshift of tracer QSOs to read, to ensure no
            double-counting with Lya mocks.  Defaults to None.
        target_name : :class:`str`
            Name of the target being read (e.g., ELG, LRG).
        mock_density : :class:`bool`, optional
            Compute and return the median target density in the mock.  Defaults
            to False.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.

        Returns
        -------
        :class:`dict`
            Dictionary with various keys (to be documented).

        Raises
        ------
        IOError
            If the mock data file is not found.
        ValueError
            If mockfile is not defined or if nside is not a scalar.

        """
        if mockfile is None:
            log.warning('Mockfile input is required.')
            raise ValueError

        try:
            mockfile = mockfile.format(**os.environ)
        except KeyError as e:
            log.warning('Environment variable not set for mockfile: {}'.format(e))
            raise ValueError
        
        if not os.path.isfile(mockfile):
            log.warning('Mock file {} not found!'.format(mockfile))
            raise IOError

        # Default set of healpixels is the whole DESI footprint.
        if healpixels is None:
            if nside is None:
                nside = 16
            log.info('Reading the whole DESI footprint with nside = {}.'.format(nside))
            healpixels = footprint.tiles2pix(nside)

        if nside is None:
            log.warning('Nside must be a scalar input.')
            raise ValueError

        # Read the ra,dec coordinates, pixel weight map, generate mockid, and
        # then restrict to the desired healpixels.
        if self.cached_radec is None:
            ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
            ReadGaussianField.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
        else:
            cached_mockfile, cached_nside, ra, dec, allpix, pixweight = ReadGaussianField.cached_radec
            if cached_mockfile != mockfile or cached_nside != nside:
                ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
                ReadGaussianField.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
            else:
                log.info('Using cached coordinates, healpixels, and pixel weights from {}'.format(mockfile))
                _, _, ra, dec, allpix, pixweight = ReadGaussianField.cached_radec

        mockid = np.arange(len(ra)) # unique ID/row number
        
        fracarea = pixweight[allpix]        
        cut = np.where( np.in1d(allpix, healpixels) * (fracarea > 0) )[0] # force DESI footprint

        nobj = len(cut)
        if nobj == 0:
            log.warning('No {}s in healpixels {}!'.format(target_name, healpixels))
            return dict()

        log.info('Trimmed to {} {}s in {} healpixel(s)'.format(
            nobj, target_name, len(np.atleast_1d(healpixels))))

        mockid = mockid[cut]
        allpix = allpix[cut]
        weight = 1 / fracarea[cut]
        ra = ra[cut]
        dec = dec[cut]

        # Add redshifts.
        if target_name.upper() == 'SKY':
            zz = np.zeros(len(ra))
        else:
            data = fitsio.read(mockfile, columns=['Z_COSMO', 'DZ_RSD'], upper=True, ext=1, rows=cut)
            zz = (data['Z_COSMO'].astype('f8') + data['DZ_RSD'].astype('f8')).astype('f4')
            zz_norsd = data['Z_COSMO'].astype('f4')

            # cut on maximum redshift
            if zmax_qso is not None:
                cut = np.where( zz < zmax_qso )[0]
                nobj = len(cut)
                log.info('Trimmed to {} objects with z<{:.3f}'.format(nobj, zmax_qso))
                if nobj == 0:
                    return dict()
                mockid = mockid[cut]
                allpix = allpix[cut]
                weight = weight[cut]
                ra = ra[cut]
                dec = dec[cut]
                zz = zz[cut]
                zz_norsd = zz_norsd[cut]

        # Get photometry and morphologies by sampling from the Gaussian
        # mixture models.
        isouth = self.is_south(dec)
        gmmout = self.sample_GMM(nobj, target=target_name, isouth=isouth,
                                 seed=seed, prior_redshift=zz)

        # Pack into a basic dictionary.
        out = {'TARGET_NAME': target_name, 'MOCKFORMAT': 'gaussianfield',
               'HEALPIX': allpix, 'NSIDE': nside, 'WEIGHT': weight,
               'MOCKID': mockid, 'BRICKNAME': self.Bricks.brickname(ra, dec),
               'BRICKID': self.Bricks.brickid(ra, dec),
               'RA': ra, 'DEC': dec, 'Z': zz, 'Z_NORSD': zz_norsd,
               'SOUTH': isouth}
        if gmmout is not None:
            out.update(gmmout)

        # Add MW transmission and the imaging depth.
        self.mw_transmission(out)
        self.imaging_depth(out)

        # Optionally compute the mean mock density.
        if mock_density:
            out['MOCK_DENSITY'] = self.mock_density(mockfile=mockfile)

        return out

class ReadUniformSky(SelectTargets):
    """Read a uniform sky style mock catalog."""
    cached_radec = None
    
    def __init__(self, **kwargs):
        super(ReadUniformSky, self).__init__(**kwargs)

    def readmock(self, mockfile=None, healpixels=None, nside=None,
                 target_name='', mock_density=False):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        target_name : :class:`str`
            Name of the target being read (e.g., ELG, LRG).
        mock_density : :class:`bool`, optional
            Compute and return the median target density in the mock.  Defaults
            to False.

        Returns
        -------
        :class:`dict`
            Dictionary with various keys (to be documented).

        Raises
        ------
        IOError
            If the mock data file is not found.
        ValueError
            If mockfile is not defined or if nside is not a scalar.

        """
        if mockfile is None:
            log.warning('Mockfile input is required.')
            raise ValueError

        try:
            mockfile = mockfile.format(**os.environ)
        except KeyError as e:
            log.warning('Environment variable not set for mockfile: {}'.format(e))
            raise ValueError
        
        if not os.path.isfile(mockfile):
            log.warning('Mock file {} not found!'.format(mockfile))
            raise IOError

        # Default set of healpixels is the whole DESI footprint.
        if healpixels is None:
            if nside is None:
                nside = 16
            log.info('Reading the whole DESI footprint with nside = {}.'.format(nside))
            healpixels = footprint.tiles2pix(nside)

        if nside is None:
            log.warning('Nside must be a scalar input.')
            raise ValueError

        # Read the ra,dec coordinates, pixel weight map, generate mockid, and
        # then restrict to the desired healpixels.
        if self.cached_radec is None:
            ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
            ReadUniformSky.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
        else:
            cached_mockfile, cached_nside, ra, dec, allpix, pixweight = ReadUniformSky.cached_radec
            if cached_mockfile != mockfile or cached_nside != nside:
                ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
                ReadUniformSky.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
            else:
                log.info('Using cached coordinates, healpixels, and pixel weights from {}'.format(mockfile))
                _, _, ra, dec, allpix, pixweight = ReadUniformSky.cached_radec

        mockid = np.arange(len(ra)) # unique ID/row number

        fracarea = pixweight[allpix]
        cut = np.where( np.in1d(allpix, healpixels) * (fracarea > 0) )[0] # force DESI footprint

        nobj = len(cut)
        if nobj == 0:
            log.warning('No {}s in healpixels {}!'.format(target_name, healpixels))
            return dict()

        log.info('Trimmed to {} {}s in {} healpixel(s).'.format(
            nobj, target_name, len(np.atleast_1d(healpixels))))

        mockid = mockid[cut]
        allpix = allpix[cut]
        weight = 1 / fracarea[cut]
        ra = ra[cut]
        dec = dec[cut]

        # Pack into a basic dictionary.
        out = {'TARGET_NAME': target_name, 'MOCKFORMAT': 'uniformsky',
               'HEALPIX': allpix, 'NSIDE': nside, 'WEIGHT': weight,
               'MOCKID': mockid, 'BRICKNAME': self.Bricks.brickname(ra, dec),
               'BRICKID': self.Bricks.brickid(ra, dec),
               'RA': ra, 'DEC': dec, 'Z': np.zeros(len(ra))}

        # Add MW transmission and the imaging depth.
        self.mw_transmission(out)
        self.imaging_depth(out)

        # Optionally compute the mean mock density.
        if mock_density:
            out['MOCK_DENSITY'] = self.mock_density(mockfile=mockfile)

        return out

class ReadGalaxia(SelectTargets):
    """Read a Galaxia style mock catalog."""
    cached_pixweight = None

    def __init__(self, **kwargs):
        super(ReadGalaxia, self).__init__(**kwargs)

    def readmock(self, mockfile=None, healpixels=[], nside=[], nside_galaxia=8, 
                 target_name='MWS_MAIN', magcut=None):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the top-level directory of the Galaxia mock catalog.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        nside_galaxia : :class:`int`
            Healpixel nside indicating how the mock on-disk has been organized.
            Defaults to 8.
        target_name : :class:`str`
            Name of the target being read (e.g., MWS_MAIN).
        magcut : :class:`float`
            Magnitude cut (hard-coded to SDSS r-band) to subselect targets
            brighter than magcut. 

        Returns
        -------
        :class:`dict`
            Dictionary with various keys (to be documented).

        Raises
        ------
        IOError
            If the top-level Galaxia directory is not found.
        ValueError
            (1) If either mockfile or nside_galaxia are not defined; (2) if
            healpixels or nside are not scalar inputs; or (3) if the input
            target_name is not recognized.

        """
        from desitarget.targets import encode_targetid
        from desitarget.mock.io import get_healpix_dir, findfile

        if mockfile is None:
            log.warning('Mockfile input is required.')
            raise ValueError

        try:
            mockfile = mockfile.format(**os.environ)
        except KeyError as e:
            log.warning('Environment variable not set for mockfile: {}'.format(e))
            raise ValueError
        
        if nside_galaxia is None:
            log.warning('Nside_galaxia input is required.')
            raise ValueError
        
        mockfile_nside = os.path.join(mockfile, str(nside_galaxia))
        if not os.path.isdir(mockfile_nside):
            log.warning('Galaxia top-level directory {} not found!'.format(mockfile_nside))
            raise IOError

        # Because of the size of the Galaxia mock, healpixels (and nside) must
        # be scalars.
        if len(np.atleast_1d(healpixels)) != 1 and len(np.atleast_1d(nside)) != 1:
            log.warning('Healpixels and nside must be scalar inputs.')
            raise ValueError

        if self.cached_pixweight is None:
            pixweight = load_pixweight(nside, pixmap=self.pixmap)
            ReadGalaxia.cached_pixweight = (pixweight, nside)
        else:
            pixweight, cached_nside = ReadGalaxia.cached_pixweight
            if cached_nside != nside:
                pixweight = load_pixweight(nside, pixmap=self.pixmap)
                ReadGalaxia.cached_pixweight = (pixweight, nside)
            else:
                log.info('Using cached pixel weight map.')
                pixweight, _ = ReadGalaxia.cached_pixweight

        # Get the set of nside_galaxia pixels that belong to the desired
        # healpixels (which have nside).  This will break if healpixels is a
        # vector.
        theta, phi = hp.pix2ang(nside, healpixels, nest=True)
        pixnum = hp.ang2pix(nside_galaxia, theta, phi, nest=True)

        if target_name.upper() == 'MWS_MAIN':
            filetype = 'mock_allsky_galaxia_desi'
        elif target_name.upper() == 'FAINTSTAR':
            filetype = ('mock_superfaint_allsky_galaxia_desi_b10_cap_north',
                        'mock_superfaint_allsky_galaxia_desi_b10_cap_south')
        else:
            log.warning('Unrecognized target name {}!'.format(target_name))
            raise ValueError

        for ff in np.atleast_1d(filetype):
            galaxiafile = findfile(filetype=ff, nside=nside_galaxia, pixnum=pixnum,
                                   basedir=mockfile_nside, ext='fits')
            if os.path.isfile(galaxiafile):
                break

        if len(galaxiafile) == 0:
            log.warning('File {} not found!'.format(galaxiafile))
            raise IOError

        log.info('Reading {}'.format(galaxiafile))
        radec = fitsio.read(galaxiafile, columns=['RA', 'DEC'], upper=True, ext=1)
        nobj = len(radec)

        objid = np.arange(nobj)
        mockid = encode_targetid(objid=objid, brickid=pixnum, mock=1)

        allpix = footprint.radec2pix(nside, radec['RA'], radec['DEC'])

        fracarea = pixweight[allpix]
        cut = np.where( np.in1d(allpix, healpixels) * (fracarea > 0) )[0] # force DESI footprint

        nobj = len(cut)
        if nobj == 0:
            log.warning('No {}s in healpixels {}!'.format(target_name, healpixels))
            return dict()

        mockid = mockid[cut]
        objid = objid[cut]
        allpix = allpix[cut]
        weight = 1 / fracarea[cut]
        ra = radec['RA'][cut].astype('f8') % 360.0 # enforce 0 < ra < 360
        dec = radec['DEC'][cut].astype('f8')
        del radec

        cols = ['V_HELIO', 'SDSSU_TRUE_NODUST', 'SDSSG_TRUE_NODUST',
                'SDSSR_TRUE_NODUST', 'SDSSI_TRUE_NODUST', 'SDSSZ_TRUE_NODUST',
                'SDSSR_OBS', 'TEFF', 'LOGG', 'FEH']
        data = fitsio.read(galaxiafile, columns=cols, upper=True, ext=1, rows=cut)
        zz = (data['V_HELIO'].astype('f4') / C_LIGHT).astype('f4')
        mag = data['SDSSR_TRUE_NODUST'].astype('f4') # SDSS r-band, extinction-corrected
        mag_obs = data['SDSSR_OBS'].astype('f4')     # SDSS r-band, observed
        teff = 10**data['TEFF'].astype('f4')         # log10!
        logg = data['LOGG'].astype('f4')
        feh = data['FEH'].astype('f4')

        if magcut:
            cut = mag < magcut
            if np.count_nonzero(cut) == 0:
                log.warning('No objects with r < {}!'.format(magcut))
                return dict()
            else:
                mockid = mockid[cut]
                objid = objid[cut]
                allpix = allpix[cut]
                weight = weight[cut]
                ra = ra[cut]
                dec = dec[cut]
                zz = zz[cut]
                mag = mag[cut]
                mag_obs = mag_obs[cut]
                teff = teff[cut]
                logg = logg[cut]
                feh = feh[cut]
                nobj = len(ra)
                log.info('Trimmed to {} {}s with r < {}.'.format(nobj, target_name, magcut))

        # Temporary hack to read some Gaia columns from a separate file, but
        # only for the MWS_MAIN mocks!
        if target_name.upper() == 'MWS_MAIN':
            gaiafile = galaxiafile.replace('mock_', 'gaia_mock_')
            if os.path.isfile(gaiafile):
                cols = ['G_GAIA', 'PM_RA_STAR_GAIA', 'PM_DEC_GAIA', 'PARALLAX_GAIA',
                        'PARALLAX_GAIA_ERROR', 'PM_RA_GAIA_ERROR', 'PM_DEC_GAIA_ERROR']
                gaia = fitsio.read(gaiafile, columns=cols, upper=True, ext=1, rows=cut)
                    
        elif target_name.upper() == 'FAINTSTAR': # Hack for FAINTSTAR

            #from astropy.table import Table
            #morecols = ['PM_RA', 'PM_DEC', 'DM']
            #moredata = fitsio.read(galaxiafile, columns=morecols, upper=True, ext=1, rows=objid)

            gaia = Table()
            gaia['G_GAIA'] = mag # hack!
            gaia['PM_RA_STAR_GAIA'] = np.zeros(nobj)  # moredata['PM_RA']
            gaia['PM_DEC_GAIA'] = np.zeros(nobj)      # moredata['PM_DEC']
            gaia['PARALLAX_GAIA'] = np.zeros(nobj)+20 # moredata['D_HELIO'] / 206265.
            gaia['PARALLAX_GAIA_ERROR'] = np.zeros(nobj)+1e8
            gaia['PM_RA_GAIA_ERROR'] = np.zeros(nobj)+1e8
            gaia['PM_DEC_GAIA_ERROR'] = np.zeros(nobj)+1e8
        else:
            pass
        
        # Pack into a basic dictionary.
        out = {'TARGET_NAME': target_name, 'MOCKFORMAT': 'galaxia',
               'HEALPIX': allpix, 'NSIDE': nside, 'WEIGHT': weight,
               'MOCKID': mockid, 'BRICKNAME': self.Bricks.brickname(ra, dec),
               'BRICKID': self.Bricks.brickid(ra, dec),
               'RA': ra, 'DEC': dec, 'Z': zz, 'MAG': mag, 'MAG_OBS': mag_obs,
               'TEFF': teff, 'LOGG': logg, 'FEH': feh,
               'MAGFILTER': np.repeat('sdss2010-r', nobj),
               'REF_ID': mockid,

               'GAIA_PHOT_G_MEAN_MAG': gaia['G_GAIA'].astype('f4'),
               #'GAIA_PHOT_G_MEAN_FLUX_OVER_ERROR' - f4
               'GAIA_PHOT_BP_MEAN_MAG': np.zeros(nobj).astype('f4'), # placeholder
               #'GAIA_PHOT_BP_MEAN_FLUX_OVER_ERROR' - f4
               'GAIA_PHOT_RP_MEAN_MAG': np.zeros(nobj).astype('f4'), # placeholder
               #'GAIA_PHOT_RP_MEAN_FLUX_OVER_ERROR' - f4
               'GAIA_ASTROMETRIC_EXCESS_NOISE': np.zeros(nobj).astype('f4'), # placeholder
               #'GAIA_DUPLICATED_SOURCE' - b1 # default is False
               'PARALLAX': gaia['PARALLAX_GAIA'].astype('f4'),
               'PARALLAX_IVAR': np.zeros(nobj).astype('f4'),
               'PMRA': gaia['PM_RA_STAR_GAIA'].astype('f4'),
               'PMRA_IVAR': np.zeros(nobj).astype('f4'),
               'PMDEC': gaia['PM_DEC_GAIA'].astype('f4'), # no _STAR_!
               'PMDEC_IVAR': np.zeros(nobj).astype('f4'),
              
               'SOUTH': self.is_south(dec), 'TYPE': 'PSF'}

        # Handle ivars -- again, a temporary hack
        for outkey, gaiakey in zip( ('PARALLAX_IVAR', 'PMRA_IVAR', 'PMDEC_IVAR'),
                                     ('PARALLAX_GAIA_ERROR', 'PM_RA_GAIA_ERROR', 'PM_DEC_GAIA_ERROR') ):
            good = gaia[gaiakey] > 0
            if np.sum(good) > 0:
                out[outkey][good] = (1/gaia[gaiakey]**2).astype('f4')

        # Add MW transmission and the imaging depth.
        self.mw_transmission(out)
        self.imaging_depth(out)

        return out

class ReadLyaCoLoRe(SelectTargets):
    """Read a CoLoRe mock catalog of Lya skewers."""
    def __init__(self, **kwargs):
        super(ReadLyaCoLoRe, self).__init__(**kwargs)

    def readmock(self, mockfile=None, healpixels=None, nside=None,
                 target_name='LYA', nside_lya=16, zmin_lya=None,
                 mock_density=False):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the top-level directory of the CoLoRe mock catalog.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        target_name : :class:`str`
            Name of the target being read (if not LYA).
        nside_lya : :class:`int`
            Healpixel nside indicating how the mock on-disk has been organized.
            Defaults to 16.
        zmin_lya : :class:`float`
            Minimum redshift of Lya skewers, to ensure no double-counting with
            QSO mocks.  Defaults to None.
        mock_density : :class:`bool`, optional
            Compute and return the median target density in the mock.  Defaults
            to False.

        Returns
        -------
        :class:`dict`
            Dictionary with various keys (to be documented).

        Raises
        ------
        IOError
            If the top-level mock data file is not found.
        ValueError
            If mockfile, nside, or nside_lya are not defined.

        """
        if mockfile is None:
            log.warning('Mockfile input is required.')
            raise ValueError
        
        try:
            mockfile = mockfile.format(**os.environ)
        except KeyError as e:
            log.warning('Environment variable not set for mockfile: {}'.format(e))
            raise ValueError
        
        if nside_lya is None:
            log.warning('Nside_lya input is required.')
            raise ValueError
        
        if not os.path.isfile(mockfile):
            log.warning('Mock file {} not found!'.format(mockfile))
            raise IOError

        mockdir = os.path.dirname(mockfile)
    
        # Default set of healpixels is the whole DESI footprint.
        if healpixels is None:
            if nside is None:
                nside = 16
            log.info('Reading the whole DESI footprint with nside = {}.'.format(nside))
            healpixels = footprint.tiles2pix(nside)

        if nside is None:
            log.warning('Nside must be a scalar input.')
            raise ValueError

        pixweight = load_pixweight(nside, pixmap=self.pixmap)

        # Read the ra,dec coordinates and then restrict to the desired
        # healpixels.
        log.info('Reading {}'.format(mockfile))
        try: # new data model
            tmp = fitsio.read(mockfile, columns=['RA', 'DEC', 'MOCKID', 'Z_QSO_RSD',
                                                 'Z_QSO_NO_RSD', 'PIXNUM'],
                              upper=True, ext=1)
            zz = tmp['Z_QSO_RSD'].astype('f4')
            zz_norsd = tmp['Z_QSO_NO_RSD'].astype('f4')
        except: # old data model
            tmp = fitsio.read(mockfile, columns=['RA', 'DEC', 'MOCKID' ,'Z', 'PIXNUM'],
                              upper=True, ext=1)
            zz = tmp['Z'].astype('f4')
            zz_norsd = tmp['Z'].astype('f4')
            
        ra = tmp['RA'].astype('f8') % 360.0 # enforce 0 < ra < 360
        dec = tmp['DEC'].astype('f8')            
        mockpix = tmp['PIXNUM']
        mockid = (tmp['MOCKID'].astype(float)).astype(int)
            
        del tmp

        log.info('Assigning healpix pixels with nside = {}'.format(nside))
        allpix = footprint.radec2pix(nside, ra, dec)

        fracarea = pixweight[allpix]
        # force DESI footprint
        cut = np.where( np.in1d(allpix, healpixels) * (fracarea > 0) )[0]

        nobj = len(cut)
        if nobj == 0:
            log.warning('No {}s in healpixels {}!'.format(target_name, healpixels))
            return dict()

        log.info('Trimmed to {} {}s in {} healpixel(s)'.format(
            nobj, target_name, len(np.atleast_1d(healpixels))))

        allpix = allpix[cut]
        weight = 1 / fracarea[cut]
        ra = ra[cut]
        dec = dec[cut]
        zz = zz[cut]
        zz_norsd = zz_norsd[cut]
        #objid = objid[cut]
        mockpix = mockpix[cut]
        mockid = mockid[cut]

        # Cut on minimum redshift.
        if zmin_lya is not None:
            cut = np.where( zz >= zmin_lya )[0]
            nobj = len(cut)
            log.info('Trimmed to {} {}s with z>={:.3f}'.format(nobj, target_name, zmin_lya))
            if nobj == 0:
                return dict()
            allpix = allpix[cut]
            weight = weight[cut]
            ra = ra[cut]
            dec = dec[cut]
            zz = zz[cut]
            zz_norsd = zz_norsd[cut]
            #objid = objid[cut]
            mockpix = mockpix[cut]
            mockid = mockid[cut]

        # Build the full filenames.
        lyafiles = []
        for mpix in mockpix:
            lyafiles.append("%s/%d/%d/transmission-%d-%d.fits"%(
                mockdir, mpix//100, mpix, nside_lya, mpix))

        # ToDo: draw magnitudes from an appropriate luminosity function!
        # 
            
        # Pack into a basic dictionary.
        out = {'TARGET_NAME': target_name, 'MOCKFORMAT': 'CoLoRe',
               'HEALPIX': allpix, 'NSIDE': nside, 'WEIGHT': weight,
               #'OBJID': objid,
               'MOCKID': mockid, 'LYAFILES': np.array(lyafiles),
               'BRICKNAME': self.Bricks.brickname(ra, dec),
               'BRICKID': self.Bricks.brickid(ra, dec),
               'RA': ra, 'DEC': dec, 'Z': zz, 'Z_NORSD': zz_norsd,
               'SOUTH': self.is_south(dec), 'TYPE': 'PSF'}

        # Add MW transmission and the imaging depth.
        self.mw_transmission(out)
        self.imaging_depth(out)

        # Optionally compute the mean mock density.
        if mock_density:
            out['MOCK_DENSITY'] = self.mock_density(mockfile=mockfile)

        return out

class ReadMXXL(SelectTargets):
    """Read a MXXL mock catalog of BGS targets."""
    cached_radec = None

    def __init__(self, **kwargs):
        super(ReadMXXL, self).__init__(**kwargs)

    def readmock(self, mockfile=None, healpixels=None, nside=None,
                 target_name='BGS', magcut=None, only_coords=False,
                 mock_density=False, seed=None):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the top-level directory of the CoLoRe mock catalog.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        target_name : :class:`str`
            Name of the target being read (if not BGS).
        magcut : :class:`float`
            Magnitude cut (hard-coded to SDSS r-band) to subselect targets
            brighter than magcut. 
        only_coords : :class:`bool`, optional
            To get some improvement in speed, only read the target coordinates
            and some other basic info.
        mock_density : :class:`bool`, optional
            Compute and return the median target density in the mock.  Defaults
            to False.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.

        Returns
        -------
        :class:`dict`
            Dictionary with various keys (to be documented).

        Raises
        ------
        IOError
            If the mock data file is not found.
        ValueError
            If mockfile is not defined or if nside is not a scalar.

        """
        import h5py
        
        if mockfile is None:
            log.warning('Mockfile input is required.')
            raise ValueError
        
        try:
            mockfile = mockfile.format(**os.environ)
        except KeyError as e:
            log.warning('Environment variable not set for mockfile: {}'.format(e))
            raise ValueError
        
        if not os.path.isfile(mockfile):
            log.warning('Mock file {} not found!'.format(mockfile))
            raise IOError

        # Default set of healpixels is the whole DESI footprint.
        if healpixels is None:
            if nside is None:
                nside = 16
            log.info('Reading the whole DESI footprint with nside = {}.'.format(nside))
            healpixels = footprint.tiles2pix(nside)

        if nside is None:
            log.warning('Nside must be a scalar input.')
            raise ValueError

        # Read the data, generate mockid, and then restrict to the input
        # healpixel.
        def _read_mockfile(mockfile, nside, pixmap):
            # Work around hdf5 <1.10 bug on /project; see
            # http://www.nersc.gov/users/data-analytics/data-management/i-o-libraries/hdf5-2/h5py/
            hdf5_flock = os.getenv('HDF5_USE_FILE_LOCKING')
            os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'
            with h5py.File(mockfile, mode='r') as f:
                ra  = f['Data/ra'][:].astype('f8') % 360.0 # enforce 0 < ra < 360
                dec = f['Data/dec'][:].astype('f8')
                zz = f['Data/z_obs'][:].astype('f4')
                rmag = f['Data/app_mag'][:].astype('f4')
                absmag = f['Data/abs_mag'][:].astype('f4')
                gr = f['Data/g_r'][:].astype('f4')

            if hdf5_flock is not None:
                os.environ['HDF5_USE_FILE_LOCKING'] = hdf5_flock
            else:
                del os.environ['HDF5_USE_FILE_LOCKING']

            log.info('Assigning healpix pixels with nside = {}'.format(nside))
            allpix = footprint.radec2pix(nside, ra, dec)

            pixweight = load_pixweight(nside, pixmap=pixmap)
        
            return ra, dec, zz, rmag, absmag, gr, allpix, pixweight

        # Read the ra,dec coordinates, pixel weight map, generate mockid, and
        # then restrict to the desired healpixels.
        if self.cached_radec is None:
            ra, dec, zz, rmag, absmag, gr, allpix, pixweight = _read_mockfile(mockfile, nside, self.pixmap)
            ReadMXXL.cached_radec = (mockfile, nside, ra, dec, zz, rmag, absmag, gr, allpix, pixweight)
        else:
            cached_mockfile, cached_nside, ra, dec, zz, rmag, absmag, gr, allpix, pixweight = ReadMXXL.cached_radec
            if cached_mockfile != mockfile or cached_nside != nside:
                ra, dec, zz, rmag, absmag, gr, allpix, pixweight = _read_mockfile(mockfile, nside, self.pixmap)
                ReadMXXL.cached_radec = (mockfile, nside, ra, dec, zz, rmag, absmag, gr, allpix, pixweight)
            else:
                log.info('Using cached coordinates, healpixels, and pixel weights from {}'.format(mockfile))
                _, _, ra, dec, zz, rmag, absmag, gr, allpix, pixweight = ReadMXXL.cached_radec

        mockid = np.arange(len(ra)) # unique ID/row number
        
        fracarea = pixweight[allpix]
        cut = np.where( np.in1d(allpix, healpixels) * (fracarea > 0) )[0] # force DESI footprint

        nobj = len(cut)
        if nobj == 0:
            log.warning('No {}s in healpixels {}!'.format(target_name, healpixels))
            return dict()

        log.info('Trimmed to {} {}s in {} healpixel(s).'.format(
            nobj, target_name, len(np.atleast_1d(healpixels))))

        mockid = mockid[cut]
        allpix = allpix[cut]
        weight = 1 / fracarea[cut]
        ra = ra[cut]
        dec = dec[cut]
        zz = zz[cut]
        rmag = rmag[cut]
        absmag = absmag[cut]
        gr = gr[cut]

        if magcut:
            cut = rmag < magcut
            if np.count_nonzero(cut) == 0:
                log.warning('No objects with r < {}!'.format(magcut))
                return dict()
            else:
                mockid = mockid[cut]
                allpix = allpix[cut]
                weight = weight[cut]
                ra = ra[cut]
                dec = dec[cut]
                zz = zz[cut]
                rmag = rmag[cut]
                absmag = absmag[cut]
                gr = gr[cut]
                nobj = len(ra)
                log.info('Trimmed to {} {}s with r < {}.'.format(nobj, target_name, magcut))

        # Optionally (for a little more speed) only return some basic info. 
        if only_coords:
            return {'MOCKID': mockid, 'RA': ra, 'DEC': dec, 'Z': zz,
                    'MAG': rmag, 'WEIGHT': weight, 'NSIDE': nside}

        # Get photometry and morphologies by sampling from the Gaussian mixture
        # models.  This is a total hack because our apparent magnitudes (rmag)
        # will not be consistent with the Gaussian draws.  But as a hack just
        # sort the shapes and sizes on rmag.
        isouth = self.is_south(dec)
        gmmout = self.sample_GMM(nobj, target=target_name, isouth=isouth,
                                 seed=seed, prior_mag=rmag)

        # Pack into a basic dictionary.
        out = {'TARGET_NAME': target_name, 'MOCKFORMAT': 'durham_mxxl_hdf5',
               'HEALPIX': allpix, 'NSIDE': nside, 'WEIGHT': weight,
               'MOCKID': mockid, 'BRICKNAME': self.Bricks.brickname(ra, dec),
               'BRICKID': self.Bricks.brickid(ra, dec),
               'RA': ra, 'DEC': dec, 'Z': zz, 'MAG': rmag, 'SDSS_absmag_r01': absmag,
               'SDSS_01gr': gr, 'MAGFILTER': np.repeat('sdss2010-r', nobj),
               'SOUTH': isouth}
        if gmmout is not None:
            out.update(gmmout)

        # Add MW transmission and the imaging depth.
        self.mw_transmission(out)
        self.imaging_depth(out)

        # Optionally compute the mean mock density.
        if mock_density:
            out['MOCK_DENSITY'] = self.mock_density(mockfile=mockfile)

        return out

class ReadGAMA(SelectTargets):
    """Read a GAMA catalog of BGS targets.  This reader will only generally be used
    for the Survey Validation Data Challenge."""
    cached_radec = None
    
    def __init__(self, **kwargs):
        super(ReadGAMA, self).__init__(**kwargs)
        
    def readmock(self, mockfile=None, healpixels=None, nside=None,
                 target_name='', magcut=None, only_coords=False):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        target_name : :class:`str`
            Name of the target being read (e.g., ELG, LRG).
        magcut : :class:`float`
            Magnitude cut (hard-coded to SDSS r-band) to subselect targets
            brighter than magcut. 
        only_coords : :class:`bool`, optional
            To get some improvement in speed, only read the target coordinates
            and some other basic info.

        Returns
        -------
        :class:`dict`
            Dictionary with various keys (to be documented).

        Raises
        ------
        IOError
            If the mock data file is not found.
        ValueError
            If mockfile or healpixels are not defined, or if nside is not a
            scalar.

        """
        if mockfile is None:
            log.warning('Mockfile input is required.')
            raise ValueError

        try:
            mockfile = mockfile.format(**os.environ)
        except KeyError as e:
            log.warning('Environment variable not set for mockfile: {}'.format(e))
            raise ValueError
        
        if not os.path.isfile(mockfile):
            log.warning('Mock file {} not found!'.format(mockfile))
            raise IOError

        # Require healpixels, or could pass the set of tiles and use
        # footprint.tiles2pix() to convert to healpixels given nside.
        if healpixels is None:
            log.warning('Healpixels input is required.') 
            raise ValueError
        
        if nside is None:
            log.warning('Nside must be a scalar input.')
            raise ValueError

        # Read the ra,dec coordinates, pixel weight map, generate mockid, and
        # then restrict to the desired healpixels.
        if self.cached_radec is None:
            ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
            ReadGAMA.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
        else:
            cached_mockfile, cached_nside, ra, dec, allpix, pixweight = ReadGAMA.cached_radec
            if cached_mockfile != mockfile or cached_nside != nside:
                ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
                ReadGAMA.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
            else:
                log.info('Using cached coordinates, healpixels, and pixel weights from {}'.format(mockfile))
                _, _, ra, dec, allpix, pixweight = ReadGAMA.cached_radec

        mockid = np.arange(len(ra)) # unique ID/row number
        
        fracarea = pixweight[allpix]
        cut = np.where( np.in1d(allpix, healpixels) * (fracarea > 0) )[0] # force DESI footprint

        nobj = len(cut)
        if nobj == 0:
            log.warning('No {}s in healpixels {}!'.format(target_name, healpixels))
            return dict()

        log.info('Trimmed to {} {}s in {} healpixel(s).'.format(
            nobj, target_name, len(np.atleast_1d(healpixels))))

        mockid = mockid[cut]
        allpix = allpix[cut]
        weight = 1 / fracarea[cut]
        ra = ra[cut]
        dec = dec[cut]

        # Add photometry, absolute magnitudes, and redshifts.
        columns = ['FLUX_G', 'FLUX_R', 'FLUX_Z', 'Z', 'UGRIZ_ABSMAG_01']
        data = fitsio.read(mockfile, columns=columns, upper=True, ext=1, rows=cut)
        zz = data['Z'].astype('f4')
        rmag = 22.5 - 2.5 * np.log10(data['FLUX_R']).astype('f4')

        # Pack into a basic dictionary.  Could include shapes and other spectral
        # properties here.
        out = {'TARGET_NAME': target_name, 'MOCKFORMAT': 'bgs-gama',
               'HEALPIX': allpix, 'NSIDE': nside, 'WEIGHT': weight,
               'MOCKID': mockid, 'BRICKNAME': self.Bricks.brickname(ra, dec),
               'BRICKID': self.Bricks.brickid(ra, dec),
               'RA': ra, 'DEC': dec, 'Z': zz, 'RMABS_01': data['UGRIZ_ABSMAG_01'][:, 2],
               'UG_01': data['UGRIZ_ABSMAG_01'][:, 0]-data['UGRIZ_ABSMAG_01'][:, 1],
               'GR_01': data['UGRIZ_ABSMAG_01'][:, 1]-data['UGRIZ_ABSMAG_01'][:, 2],
               'RI_01': data['UGRIZ_ABSMAG_01'][:, 2]-data['UGRIZ_ABSMAG_01'][:, 3],
               'IZ_01': data['UGRIZ_ABSMAG_01'][:, 3]-data['UGRIZ_ABSMAG_01'][:, 4],
               'MAGFILTER': np.repeat('decam2014-r', nobj),
               'MAG': rmag, 'SOUTH': self.is_south(dec)}

        # Add MW transmission and the imaging depth.
        self.mw_transmission(out)
        self.imaging_depth(out)

        return out

class ReadMWS_WD(SelectTargets):
    """Read a mock catalog of Milky Way Survey white dwarf targets (MWS_WD)."""
    cached_radec = None

    def __init__(self, **kwargs):
        super(ReadMWS_WD, self).__init__(**kwargs)

    def readmock(self, mockfile=None, healpixels=None, nside=None,
                 target_name='WD', mock_density=False):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        target_name : :class:`str`
            Name of the target being read (if not WD).
        mock_density : :class:`bool`, optional
            Compute and return the median target density in the mock.  Defaults
            to False.

        Returns
        -------
        :class:`dict`
            Dictionary with various keys (to be documented).

        Raises
        ------
        IOError
            If the mock data file is not found.
        ValueError
            If mockfile is not defined or if nside is not a scalar.

        """
        if mockfile is None:
            log.warning('Mockfile input is required.')
            raise ValueError
        
        try:
            mockfile = mockfile.format(**os.environ)
        except KeyError as e:
            log.warning('Environment variable not set for mockfile: {}'.format(e))
            raise ValueError
        
        if not os.path.isfile(mockfile):
            log.warning('Mock file {} not found!'.format(mockfile))
            raise IOError

        # Default set of healpixels is the whole DESI footprint.
        if healpixels is None:
            if nside is None:
                nside = 16
            log.info('Reading the whole DESI footprint with nside = {}.'.format(nside))
            healpixels = footprint.tiles2pix(nside)

        if nside is None:
            log.warning('Nside must be a scalar input.')
            raise ValueError

        # Read the ra,dec coordinates, pixel weight map, generate mockid, and
        # then restrict to the desired healpixels.
        if self.cached_radec is None:
            ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
            ReadMWS_WD.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
        else:
            cached_mockfile, cached_nside, ra, dec, allpix, pixweight = ReadMWS_WD.cached_radec
            if cached_mockfile != mockfile or cached_nside != nside:
                ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
                ReadMWS_WD.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
            else:
                log.info('Using cached coordinates, healpixels, and pixel weights from {}'.format(mockfile))
                _, _, ra, dec, allpix, pixweight = ReadMWS_WD.cached_radec

        mockid = np.arange(len(ra)) # unique ID/row number

        fracarea = pixweight[allpix]
        cut = np.where( np.in1d(allpix, healpixels) * (fracarea > 0) )[0] # force DESI footprint

        nobj = len(cut)
        if nobj == 0:
            log.warning('No {}s in healpixels {}!'.format(target_name, healpixels))
            return dict()

        log.info('Trimmed to {} {}s in {} healpixel(s).'.format(
            nobj, target_name, len(np.atleast_1d(healpixels))))

        mockid = mockid[cut]
        allpix = allpix[cut]
        weight = 1 / fracarea[cut]
        ra = ra[cut]
        dec = dec[cut]

        cols = ['RADIALVELOCITY', 'G_SDSS', 'TEFF', 'LOGG', 'SPECTRALTYPE']
        data = fitsio.read(mockfile, columns=cols, upper=True, ext=1, rows=cut)
        zz = (data['RADIALVELOCITY'] / C_LIGHT).astype('f4')
        mag = data['G_SDSS'].astype('f4') # SDSS g-band
        teff = data['TEFF'].astype('f4')
        logg = data['LOGG'].astype('f4')
        templatesubtype = np.char.upper(data['SPECTRALTYPE'].astype('<U'))

        # Pack into a basic dictionary.
        out = {'TARGET_NAME': target_name, 'MOCKFORMAT': 'mws_wd',
               'HEALPIX': allpix, 'NSIDE': nside, 'WEIGHT': weight,
               'MOCKID': mockid, 'BRICKNAME': self.Bricks.brickname(ra, dec),
               'BRICKID': self.Bricks.brickid(ra, dec),
               'RA': ra, 'DEC': dec, 'Z': zz, 'MAG': mag, 'TEFF': teff, 'LOGG': logg,
               'MAGFILTER': np.repeat('sdss2010-g', nobj),
               'TEMPLATESUBTYPE': templatesubtype,
               'SOUTH': self.is_south(dec), 'TYPE': 'PSF'}

        # Add MW transmission and the imaging depth.
        self.mw_transmission(out)
        self.imaging_depth(out)

        # Optionally compute the mean mock density.
        if mock_density:
            out['MOCK_DENSITY'] = self.mock_density(mockfile=mockfile)

        return out
    
class ReadMWS_NEARBY(SelectTargets):
    """Read a mock catalog of Milky Way Survey nearby targets (MWS_NEARBY)."""
    cached_radec = None
    
    def __init__(self, **kwargs):
        super(ReadMWS_NEARBY, self).__init__(**kwargs)

    def readmock(self, mockfile=None, healpixels=None, nside=None,
                 target_name='MWS_NEARBY', mock_density=False):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        target_name : :class:`str`
            Name of the target being read (if not MWS_NEARBY).
        mock_density : :class:`bool`, optional
            Compute and return the median target density in the mock.  Defaults
            to False.

        Returns
        -------
        :class:`dict`
            Dictionary with various keys (to be documented).

        Raises
        ------
        IOError
            If the mock data file is not found.
        ValueError
            If mockfile is not defined or if nside is not a scalar.

        """
        if mockfile is None:
            log.warning('Mockfile input is required.')
            raise ValueError

        try:
            mockfile = mockfile.format(**os.environ)
        except KeyError as e:
            log.warning('Environment variable not set for mockfile: {}'.format(e))
            raise ValueError
        
        if not os.path.isfile(mockfile):
            log.warning('Mock file {} not found!'.format(mockfile))
            raise IOError

        # Default set of healpixels is the whole DESI footprint.
        if healpixels is None:
            if nside is None:
                nside = 16
            log.info('Reading the whole DESI footprint with nside = {}.'.format(nside))
            healpixels = footprint.tiles2pix(nside)

        if nside is None:
            log.warning('Nside must be a scalar input.')
            raise ValueError

        # Read the ra,dec coordinates, pixel weight map, generate mockid, and
        # then restrict to the desired healpixels.
        if self.cached_radec is None:
            ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
            ReadMWS_NEARBY.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
        else:
            cached_mockfile, cached_nside, ra, dec, allpix, pixweight = ReadMWS_NEARBY.cached_radec
            if cached_mockfile != mockfile or cached_nside != nside:
                ra, dec, allpix, pixweight = _get_radec(mockfile, nside, self.pixmap)
                ReadMWS_NEARBY.cached_radec = (mockfile, nside, ra, dec, allpix, pixweight)
            else:
                log.info('Using cached coordinates, healpixels, and pixel weights from {}'.format(mockfile))
                _, _, ra, dec, allpix, pixweight = ReadMWS_NEARBY.cached_radec
        
        mockid = np.arange(len(ra)) # unique ID/row number

        fracarea = pixweight[allpix]
        cut = np.where( np.in1d(allpix, healpixels) * (fracarea > 0) )[0] # force DESI footprint

        nobj = len(cut)
        if nobj == 0:
            log.warning('No {}s in healpixels {}!'.format(target_name, healpixels))
            return dict()

        log.info('Trimmed to {} {}s in {} healpixel(s).'.format(
            nobj, target_name, len(np.atleast_1d(healpixels))))

        mockid = mockid[cut]
        allpix = allpix[cut]
        weight = 1 / fracarea[cut]
        ra = ra[cut]
        dec = dec[cut]

        cols = ['RADIALVELOCITY', 'MAGG', 'TEFF', 'LOGG', 'FEH', 'SPECTRALTYPE']
        data = fitsio.read(mockfile, columns=cols, upper=True, ext=1, rows=cut)
        zz = (data['RADIALVELOCITY'] / C_LIGHT).astype('f4')
        mag = data['MAGG'].astype('f4') # SDSS g-band
        teff = data['TEFF'].astype('f4')
        logg = data['LOGG'].astype('f4')
        feh = data['FEH'].astype('f4')
        templatesubtype = data['SPECTRALTYPE']

        # Pack into a basic dictionary.  Is the normalization filter g-band???
        out = {'TARGET_NAME': target_name, 'MOCKFORMAT': 'mws_100pc',
               'HEALPIX': allpix, 'NSIDE': nside, 'WEIGHT': weight,
               'MOCKID': mockid, 'BRICKNAME': self.Bricks.brickname(ra, dec),
               'BRICKID': self.Bricks.brickid(ra, dec),
               'RA': ra, 'DEC': dec, 'Z': zz, 'MAG': mag, 'TEFF': teff, 'LOGG': logg, 'FEH': feh,
               'MAGFILTER': np.repeat('sdss2010-g', nobj), 'TEMPLATESUBTYPE': templatesubtype,
               'SOUTH': self.is_south(dec), 'TYPE': 'PSF'}

        # Add MW transmission and the imaging depth.
        self.mw_transmission(out)
        self.imaging_depth(out)

        # Optionally compute the mean mock density.
        if mock_density:
            out['MOCK_DENSITY'] = self.mock_density(mockfile=mockfile)
            
        return out

class QSOMaker(SelectTargets):
    """Read QSO mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.
    use_simqso : :class:`bool`, optional
        Use desisim.templates.SIMQSO to generated templates rather than
        desisim.templates.QSO.  Defaults to True.

    """
    wave, template_maker = None, None
    GMM_QSO, GMM_nospectra = None, None
    
    def __init__(self, seed=None, use_simqso=True, **kwargs):
        from desisim.templates import SIMQSO, QSO
        from desiutil.sklearn import GaussianMixtureModel

        super(QSOMaker, self).__init__()

        self.seed = seed
        self.objtype = 'QSO'
        self.use_simqso = use_simqso

        if self.wave is None:
            QSOMaker.wave = _default_wave()

        if self.template_maker is None:
            if self.use_simqso:
                QSOMaker.template_maker = SIMQSO(wave=self.wave)
            else:
                QSOMaker.template_maker = QSO(wave=self.wave)

        if self.GMM_QSO is None:
            self.read_GMM(target='QSO')

        if self.GMM_nospectra is None:
            gmmfile = resource_filename('desitarget', 'mock/data/quicksurvey_gmm_qso.fits')
            QSOMaker.GMM_nospectra = GaussianMixtureModel.load(gmmfile)
            
    def read(self, mockfile=None, mockformat='gaussianfield', healpixels=None,
             nside=None, zmax_qso=None, mock_density=False, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'gaussianfield'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        zmax_qso : :class:`float`
            Maximum redshift of tracer QSOs to read, to ensure no
            double-counting with Lya mocks.  Defaults to None.
        mock_density : :class:`bool`, optional
            Compute the median target density in the mock.  Defaults to False.

        Returns
        -------
        data : :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        
        if self.mockformat == 'gaussianfield':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'GaussianRandomField', 'v0.0.8_2LPT', 'QSO.fits')
            MockReader = ReadGaussianField()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile
            
        data = MockReader.readmock(mockfile, target_name=self.objtype,
                                   healpixels=healpixels, nside=nside,
                                   zmax_qso=zmax_qso, mock_density=mock_density)

        return data

    def make_spectra(self, data=None, indx=None, seed=None, no_spectra=False):
        """Generate tracer QSO spectra.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        no_spectra : :class:`bool`, optional
            Do not generate spectra.  Defaults to False.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        objtruth : :class:`astropy.table.Table`
            Corresponding objtype-specific truth table (if applicable).
        
        """
        if seed is None:
            seed = self.seed

        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)
            
        rand = np.random.RandomState(seed)
        if no_spectra:
            flux = []
            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            meta['SEED'][:] = rand.randint(2**31, size=nobj)
            meta['REDSHIFT'][:] = data['Z'][indx]
            self.sample_gmm_nospectra(meta, rand=rand) # noiseless photometry from pre-computed GMMs
        else:
            # Sample from the north/south GMMs
            south = np.where( data['SOUTH'][indx] == True )[0]
            north = np.where( data['SOUTH'][indx] == False )[0]

            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype, simqso=self.use_simqso)
            flux = np.zeros([nobj, len(self.wave)], dtype='f4')

            if self.use_simqso:
                for these, issouth in zip( (north, south), (False, True) ):
                    if len(these) > 0:
                        flux1, _, meta1, objmeta1 = self.template_maker.make_templates(
                            nmodel=len(these), redshift=np.atleast_1d(data['Z'][indx][these]),
                            seed=seed, lyaforest=False, nocolorcuts=True, south=issouth)

                        meta[these] = meta1
                        objmeta[these] = objmeta1
                        flux[these, :] = flux1
            else:
                input_meta = empty_metatable(nmodel=nobj, objtype=self.objtype, input_meta=True)
                input_meta['SEED'][:] = rand.randint(2**31, size=nobj)
                input_meta['REDSHIFT'][:] = data['Z'][indx]
                
                if self.mockformat == 'gaussianfield':
                    input_meta['MAG'][:] = data['MAG'][indx]
                    input_meta['MAGFILTER'][:] = data['MAGFILTER'][indx]

                for these, issouth in zip( (north, south), (False, True) ):
                    if len(these) > 0:
                        flux1, _, meta1, objmeta1 = self.template_maker.make_templates(
                            input_meta=input_meta[these], lyaforest=False, nocolorcuts=True,
                            south=issouth)

                        meta[these] = meta1
                        objmeta[these] = objmeta1
                        flux[these, :] = flux1

        targets, truth, objtruth = self.populate_targets_truth(
            data, meta, objmeta, indx=indx, psf=True, use_simqso=self.use_simqso,
            seed=seed, truespectype='QSO', templatetype='QSO')

        return flux, self.wave, targets, truth, objtruth

    def select_targets(self, targets, truth, **kwargs):
        """Select QSO targets.  Input tables are modified in place.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        if self.use_simqso:
            desi_target, bgs_target, mws_target = apply_cuts(targets, tcnames='QSO')
        else:
            desi_target, bgs_target, mws_target = apply_cuts(
                targets, tcnames='QSO', qso_selection='colorcuts',
                qso_optical_cuts=True)

        targets['DESI_TARGET'] |= desi_target
        targets['BGS_TARGET'] |= bgs_target
        targets['MWS_TARGET'] |= mws_target

class LYAMaker(SelectTargets):
    """Read LYA mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.
    balprob : :class:`float`, optional
        Probability of a including one or more BALs.  Defaults to 0.0. 
    add_dla : :class:`bool`, optional
        Statistically include DLAs along the line of sight.

    """
    wave, template_maker, GMM_nospectra = None, None, None

    def __init__(self, seed=None, use_simqso=True, balprob=0.0, add_dla=False, **kwargs):
        from desisim.templates import SIMQSO, QSO
        from desiutil.sklearn import GaussianMixtureModel

        super(LYAMaker, self).__init__()

        self.seed = seed
        self.objtype = 'LYA'
        self.use_simqso = use_simqso
        self.balprob = balprob
        self.add_dla = add_dla

        if balprob > 0:
            from desisim.bal import BAL
            self.BAL = BAL()

        if self.wave is None:
            LYAMaker.wave = _default_wave()
            
        if self.template_maker is None:
            if self.use_simqso:
                LYAMaker.template_maker = SIMQSO(wave=self.wave)
            else:
                LYAMaker.template_maker = QSO(wave=self.wave)

        if self.GMM_nospectra is None:
            gmmfile = resource_filename('desitarget', 'mock/data/quicksurvey_gmm_lya.fits')
            LYAMaker.GMM_nospectra = GaussianMixtureModel.load(gmmfile)

    def read(self, mockfile=None, mockformat='CoLoRe', healpixels=None, nside=None,
             nside_lya=16, zmin_lya=None, mock_density=False, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'CoLoRe'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        nside_lya : :class:`int`
            Healpixel nside indicating how the mock on-disk has been organized.
            Defaults to 16.
        zmin_lya : :class:`float`
            Minimum redshift of Lya skewers, to ensure no double-counting with
            QSO mocks.  Defaults to None.
        mock_density : :class:`bool`, optional
            Compute the median target density in the mock.  Defaults to False.

        Returns
        -------
        :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        
        if self.mockformat == 'colore':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'lya_forest', 'london', 'v2.0', 'master.fits')
            MockReader = ReadLyaCoLoRe()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile

        data = MockReader.readmock(mockfile, target_name=self.objtype,
                                   healpixels=healpixels, nside=nside,
                                   nside_lya=nside_lya, zmin_lya=zmin_lya,
                                   mock_density=mock_density)

        return data

    def make_spectra(self, data=None, indx=None, seed=None, no_spectra=False):
        """Generate QSO spectra with the 3D Lya forest skewers included. 

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        no_spectra : :class:`bool`, optional
            Do not generate spectra.  Defaults to False.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        Raises
        ------
        KeyError
            If there is a mismatch between MOCKID in the data dictionary and the
            skewer files on-disk.

        """
        import numpy.ma as ma
        from astropy.table import vstack
        from desispec.interpolation import resample_flux
        from desisim.lya_spectra import read_lya_skewers, apply_lya_transmission
        
        if seed is None:
            seed = self.seed
            
        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        rand = np.random.RandomState(seed)
        if no_spectra:
            flux = []
            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            meta['SEED'][:] = rand.randint(2**31, size=nobj)
            meta['REDSHIFT'][:] = data['Z'][indx]
            self.sample_gmm_nospectra(meta, rand=rand) # noiseless photometry from pre-computed GMMs
        else:
            # Handle north/south photometry.
            south = np.where( data['SOUTH'][indx] == True )[0]
            north = np.where( data['SOUTH'][indx] == False )[0]
            
            if not self.use_simqso:
                input_meta = empty_metatable(nmodel=nobj, objtype=self.objtype, input_meta=True)
                input_meta['SEED'][:] = rand.randint(2**31, size=nobj)
                input_meta['REDSHIFT'][:] = data['Z'][indx]

                # These magnitudes are a total hack!
                if len(north) > 0:
                    input_meta['MAG'][north] = rand.uniform(20, 22.5, len(north)).astype('f4')
                    input_meta['MAGFILTER'][north] = 'BASS-r'
                if len(south) > 0:
                    input_meta['MAG'][south] = rand.uniform(20, 22.5, len(south)).astype('f4')
                    input_meta['MAGFILTER'][south] = 'decam2014-r'
                                
            # Read skewers.
            skewer_wave = None
            skewer_trans = None
            skewer_meta = None

            # Gather all the files containing at least one QSO skewer.
            alllyafile = data['LYAFILES'][indx]
            uniquelyafiles = sorted(set(alllyafile))

            for lyafile in uniquelyafiles:
                these = np.where( alllyafile == lyafile )[0]

                mockid_in_data = data['MOCKID'][indx][these]
                mockid_in_mock = (fitsio.read(lyafile, columns=['MOCKID'], upper=True,
                                              ext=1).astype(float)).astype(int)
                o2i = dict()
                for i, o in enumerate(mockid_in_mock):
                    o2i[o] = i
                indices_in_mock_healpix = np.zeros(mockid_in_data.size).astype(int)
                for i, o in enumerate(mockid_in_data):
                    if not o in o2i:
                        log.warning("No MOCKID={} in {}, which should never happen".format(o, lyafile))
                        raise KeyError
                    indices_in_mock_healpix[i] = o2i[o]

                # Note: there are read_dlas=False and add_metals=False options.
                tmp_wave, tmp_trans, tmp_meta, _ = read_lya_skewers(
                    lyafile, indices=indices_in_mock_healpix) 

                if skewer_wave is None:
                    skewer_wave = tmp_wave
                    dw = skewer_wave[1] - skewer_wave[0] # this is just to check same wavelength
                    skewer_trans = np.zeros((nobj, skewer_wave.size)) # allocate skewer_array
                    skewer_meta = dict()
                    for k in tmp_meta.dtype.names:
                        skewer_meta[k] = np.zeros(nobj).astype(tmp_meta[k].dtype)
                else :
                    # check wavelength is the same for all skewers
                    assert( np.max(np.abs(wave-tmp_wave)) < 0.001*dw )

                skewer_trans[these] = tmp_trans
                for k in skewer_meta.keys():
                    skewer_meta[k][these] = tmp_meta[k]

            # Check we matched things correctly.
            assert(np.max(np.abs(skewer_meta['Z']-data['Z'][indx]))<0.000001)
            assert(np.max(np.abs(skewer_meta['RA']-data['RA'][indx]))<0.000001)
            assert(np.max(np.abs(skewer_meta['DEC']-data['DEC'][indx]))<0.000001)

            # Now generate the QSO spectra simultaneously **at full wavelength
            # resolution**.  We do this because the Lya forest will have changed
            # the colors, so we need to re-synthesize the photometry below.
            meta, objmeta = empty_metatable(nmodel=nobj, objtype='QSO', simqso=self.use_simqso)
            if self.use_simqso:
                qso_flux = np.zeros([nobj, len(self.template_maker.basewave)], dtype='f4')
            else:
                qso_flux = np.zeros([nobj, len(self.template_maker.eigenwave)], dtype='f4')
                qso_wave = np.zeros_like(qso_flux)
            
            for these, issouth in zip( (north, south), (False, True) ):
                if len(these) > 0:
                    if self.use_simqso:
                        qso_flux1, qso_wave, meta1, objmeta1 = self.template_maker.make_templates(
                            nmodel=len(these), redshift=data['Z'][indx][these], seed=seed,
                            lyaforest=False, nocolorcuts=True, noresample=True, south=issouth)
                    else:
                        qso_flux1, qso_wave1, meta1, objmeta1 = self.template_maker.make_templates(
                            input_meta=input_meta[these], lyaforest=False, nocolorcuts=True,
                            noresample=True, south=issouth)
                        qso_wave[these, :] = qso_wave1
                        
                    meta[these] = meta1
                    objmeta[these] = objmeta1
                    qso_flux[these, :] = qso_flux1

            meta['SUBTYPE'][:] = 'LYA'

            # Apply the Lya forest transmission.
            _flux = apply_lya_transmission(qso_wave, qso_flux, skewer_wave, skewer_trans)

            # Add BALs
            if self.balprob > 0:
                log.debug('Adding BAL(s) with probability {}'.format(self.balprob))
                _flux, balmeta = self.BAL.insert_bals(qso_wave, _flux, meta['REDSHIFT'],
                                                      seed=self.seed,
                                                      balprob=self.balprob)
                objmeta['BAL_TEMPLATEID'][:] = balmeta['TEMPLATEID']

            # Add DLAs (ToDo).
            # ...

            # Synthesize north/south photometry.
            for these, filters in zip( (north, south), (self.template_maker.bassmzlswise, self.template_maker.decamwise) ):
                if len(these) > 0:
                    if self.use_simqso:
                        maggies = filters.get_ab_maggies(1e-17 * _flux[these, :], qso_wave.copy(), mask_invalid=True)
                        for band, filt in zip( ('FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2'), filters.names):
                            meta[band][these] = ma.getdata(1e9 * maggies[filt]) # nanomaggies
                    else:
                        # We have to loop (and pad) since each QSO has a different wavelength array.
                        maggies = []
                        for ii in range(len(these)):
                            padflux, padwave = filters.pad_spectrum(_flux[these[ii], :], qso_wave[these[ii], :], method='edge')
                            maggies.append(filters.get_ab_maggies(1e-17 * padflux, padwave.copy(), mask_invalid=True))
                            
                        maggies = vstack(maggies)
                        for band, filt in zip( ('FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2'), filters.names):
                            meta[band][these] = ma.getdata(1e9 * maggies[filt]) # nanomaggies
                            
            # Unfortunately, in order to resample to the desired output
            # wavelength vector we need to loop.
            flux = np.zeros([nobj, len(self.wave)], dtype='f4')
            if qso_wave.ndim == 2:
                for ii in range(nobj):
                    flux[ii, :] = resample_flux(self.wave, qso_wave[ii, :], _flux[ii, :], extrapolate=True)
            else:
                for ii in range(nobj):
                    flux[ii, :] = resample_flux(self.wave, qso_wave, _flux[ii, :], extrapolate=True)
                                     
        targets, truth, objtruth = self.populate_targets_truth(
                data, meta, objmeta, indx=indx, psf=True, seed=seed,
                truespectype='QSO', templatetype='QSO', templatesubtype='LYA')

        return flux, self.wave, targets, truth, objtruth

    def select_targets(self, targets, truth, **kwargs):
        """Select Lya/QSO targets.  Input tables are modified in place.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        desi_target, bgs_target, mws_target = apply_cuts(targets, tcnames='QSO')
        
        targets['DESI_TARGET'] |= desi_target
        targets['BGS_TARGET'] |= bgs_target
        targets['MWS_TARGET'] |= mws_target

class LRGMaker(SelectTargets):
    """Read LRG mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.
    nside_chunk : :class:`int`, optional
        Healpixel nside for further subdividing the sample when assigning
        velocity dispersion to targets.  Defaults to 128.

    """
    wave, tree_north, tree_south, template_maker = None, None, None, None
    GMM_LRG, GMM_nospectra = None, None
    
    def __init__(self, seed=None, nside_chunk=128, **kwargs):
        from scipy.spatial import cKDTree as KDTree
        from desisim.templates import LRG
        from desiutil.sklearn import GaussianMixtureModel

        super(LRGMaker, self).__init__()

        self.seed = seed
        self.nside_chunk = nside_chunk
        self.objtype = 'LRG'

        if self.wave is None:
            LRGMaker.wave = _default_wave()
        if self.template_maker is None:
            LRGMaker.template_maker = LRG(wave=self.wave)
            
        self.meta = self.template_maker.basemeta

        if self.tree_north is None:
            LRGMaker.tree_north = KDTree( np.vstack((
                self.meta['Z'].data)).T )
        if self.tree_south is None:
            LRGMaker.tree_south = KDTree( np.vstack((
                self.meta['Z'].data)).T )

        if self.GMM_LRG is None:
            self.read_GMM(target='LRG')

        if self.GMM_nospectra is None:
            gmmfile = resource_filename('desitarget', 'mock/data/quicksurvey_gmm_lrg.fits')
            LRGMaker.GMM_nospectra = GaussianMixtureModel.load(gmmfile)

    def read(self, mockfile=None, mockformat='gaussianfield', healpixels=None,
             nside=None, mock_density=False, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'gaussianfield'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        mock_density : :class:`bool`, optional
            Compute the median target density in the mock.  Defaults to False.

        Returns
        -------
        :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        if self.mockformat == 'gaussianfield':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'GaussianRandomField', 'v0.0.8_2LPT', 'LRG.fits')
            MockReader = ReadGaussianField()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile

        data = MockReader.readmock(mockfile, target_name=self.objtype,
                                   healpixels=healpixels, nside=nside,
                                   mock_density=mock_density, seed=self.seed)

        return data

    def make_spectra(self, data=None, indx=None, seed=None, no_spectra=False):
        """Generate LRG spectra.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        no_spectra : :class:`bool`, optional
            Do not generate spectra.  Defaults to False.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        objtruth : :class:`astropy.table.Table`
            Corresponding objtype-specific truth table (if applicable).
        
        """
        if seed is None:
            seed = self.seed
        rand = np.random.RandomState(seed)
        
        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        if no_spectra:
            flux = []
            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            meta['SEED'][:] = rand.randint(2**31, size=nobj)
            meta['REDSHIFT'][:] = data['Z'][indx]
            self.sample_gmm_nospectra(meta, rand=rand) # noiseless photometry from pre-computed GMMs
        else:
            input_meta, _ = empty_metatable(nmodel=nobj, objtype=self.objtype)
            input_meta['SEED'][:] = rand.randint(2**31, size=nobj)
            input_meta['REDSHIFT'][:] = data['Z'][indx]
            vdisp = self._sample_vdisp(data['RA'][indx], data['DEC'][indx], mean=2.3,
                                       sigma=0.1, seed=seed, nside=self.nside_chunk)

            # Differentiate north/south photometry.
            south = np.where( data['SOUTH'][indx] == True )[0]
            north = np.where( data['SOUTH'][indx] == False )[0]

            if self.mockformat == 'gaussianfield':
                # This is not quite right, but choose a template with equal probability.
                input_meta['TEMPLATEID'][:] = rand.choice(self.meta['TEMPLATEID'], nobj)
                input_meta['MAG'][:] = data['MAG'][indx]
                input_meta['MAGFILTER'][:] = data['MAGFILTER'][indx]

            # Build north/south spectra separately.
            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            flux = np.zeros([nobj, len(self.wave)], dtype='f4')

            for these, issouth in zip( (north, south), (False, True) ):
                if len(these) > 0:
                    flux1, _, meta1, objmeta1 = self.template_maker.make_templates(
                        input_meta=input_meta[these], vdisp=vdisp[these], south=issouth,
                        nocolorcuts=True)

                    meta[these] = meta1
                    objmeta[these] = objmeta1
                    flux[these, :] = flux1
                    
        targets, truth, objtruth = self.populate_targets_truth(
            data, meta, objmeta, indx=indx, psf=False, seed=seed,
            truespectype='GALAXY', templatetype='LRG')

        return flux, self.wave, targets, truth, objtruth

    def select_targets(self, targets, truth, **kwargs):
        """Select LRG targets.  Input tables are modified in place.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        desi_target, bgs_target, mws_target = apply_cuts(targets, tcnames='LRG')
        
        targets['DESI_TARGET'] |= desi_target
        targets['BGS_TARGET'] |= bgs_target
        targets['MWS_TARGET'] |= mws_target

class ELGMaker(SelectTargets):
    """Read ELG mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.
    nside_chunk : :class:`int`, optional
        Healpixel nside for further subdividing the sample when assigning
        velocity dispersion to targets.  Defaults to 128.

    """
    wave, tree_north, tree_south, template_maker = None, None, None, None
    GMM_LRG, GMM_nospectra = None, None
    
    def __init__(self, seed=None, nside_chunk=128, **kwargs):
        from scipy.spatial import cKDTree as KDTree
        from desisim.templates import ELG
        from desiutil.sklearn import GaussianMixtureModel

        super(ELGMaker, self).__init__()

        self.seed = seed
        self.nside_chunk = nside_chunk
        self.objtype = 'ELG'

        if self.wave is None:
            ELGMaker.wave = _default_wave()
        if self.template_maker is None:
            ELGMaker.template_maker = ELG(wave=self.wave)
            
        self.meta = self.template_maker.basemeta

        if self.tree_north is None:
            log.warning('Using south ELG KD Tree for north photometry.')
            ELGMaker.tree_north = KDTree( np.vstack((
                self.meta['Z'].data,
                self.meta['DECAM_G'].data - self.meta['DECAM_R'].data,
                self.meta['DECAM_R'].data - self.meta['DECAM_Z'].data)).T )
        if self.tree_south is None:
            ELGMaker.tree_south = KDTree( np.vstack((
                self.meta['Z'].data,
                self.meta['DECAM_G'].data - self.meta['DECAM_R'].data,
                self.meta['DECAM_R'].data - self.meta['DECAM_Z'].data)).T )

        if self.GMM_LRG is None:
            self.read_GMM(target='LRG')
        
        if self.GMM_nospectra is None:
            gmmfile = resource_filename('desitarget', 'mock/data/quicksurvey_gmm_elg.fits')
            ELGMaker.GMM_nospectra = GaussianMixtureModel.load(gmmfile)

    def read(self, mockfile=None, mockformat='gaussianfield', healpixels=None,
             nside=None, mock_density=False, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'gaussianfield'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        mock_density : :class:`bool`, optional
            Compute the median target density in the mock.  Defaults to False.

        Returns
        -------
        :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        if self.mockformat == 'gaussianfield':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'GaussianRandomField', 'v0.0.8_2LPT', 'ELG.fits')
            MockReader = ReadGaussianField()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile

        data = MockReader.readmock(mockfile, target_name=self.objtype,
                                   healpixels=healpixels, nside=nside,
                                   mock_density=mock_density, seed=self.seed)

        return data
            
    def make_spectra(self, data=None, indx=None, seed=None, no_spectra=False):
        """Generate ELG spectra.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        no_spectra : :class:`bool`, optional
            Do not generate spectra.  Defaults to False.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        objtruth : :class:`astropy.table.Table`
            Corresponding objtype-specific truth table (if applicable).
        
        """
        if seed is None:
            seed = self.seed
        rand = np.random.RandomState(seed)

        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        if no_spectra:
            flux = []
            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            meta['SEED'][:] = rand.randint(2**31, size=nobj)
            meta['REDSHIFT'][:] = data['Z'][indx]
            self.sample_gmm_nospectra(meta, rand=rand) # noiseless photometry from pre-computed GMMs
        else:
            input_meta, _ = empty_metatable(nmodel=nobj, objtype=self.objtype)
            input_meta['SEED'][:] = rand.randint(2**31, size=nobj)
            input_meta['REDSHIFT'][:] = data['Z'][indx]
            vdisp = self._sample_vdisp(data['RA'][indx], data['DEC'][indx], mean=1.9,
                                       sigma=0.15, seed=seed, nside=self.nside_chunk)

            # Differentiate north/south photometry.
            south = np.where( data['SOUTH'][indx] == True )[0]
            north = np.where( data['SOUTH'][indx] == False )[0]

            if self.mockformat == 'gaussianfield':
                for these, issouth in zip( (north, south), (False, True) ):
                    if len(these) > 0:
                        input_meta['MAG'][these] = data['MAG'][indx][these]
                        input_meta['MAGFILTER'][these] = data['MAGFILTER'][indx][these]
                        input_meta['TEMPLATEID'][these] = self._query(
                            np.vstack((data['Z'][indx][these],
                                       data['GR'][indx][these],
                                       data['RZ'][indx][these])).T, south=issouth)

            # Build north/south spectra separately.
            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            flux = np.zeros([nobj, len(self.wave)], dtype='f4')

            for these, issouth in zip( (north, south), (False, True) ):
                if len(these) > 0:
                    flux1, _, meta1, objmeta1 = self.template_maker.make_templates(
                        input_meta=input_meta[these], vdisp=vdisp[these], south=issouth,
                        nocolorcuts=True)

                    meta[these] = meta1
                    objmeta[these] = objmeta1
                    flux[these, :] = flux1

        targets, truth, objtruth = self.populate_targets_truth(
            data, meta, objmeta, indx=indx, psf=False, seed=seed,
            truespectype='GALAXY', templatetype='ELG')

        return flux, self.wave, targets, truth, objtruth

    def select_targets(self, targets, truth, **kwargs):
        """Select ELG targets.  Input tables are modified in place.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        desi_target, bgs_target, mws_target = apply_cuts(targets, tcnames='ELG')
        
        targets['DESI_TARGET'] |= desi_target
        targets['BGS_TARGET'] |= bgs_target
        targets['MWS_TARGET'] |= mws_target

class BGSMaker(SelectTargets):
    """Read BGS mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.
    nside_chunk : :class:`int`, optional
        Healpixel nside for further subdividing the sample when assigning
        velocity dispersion to targets.  Defaults to 128.

    """
    wave, tree, template_maker = None, None, None
    GMM_LRG, GMM_nospectra = None, None
    
    def __init__(self, seed=None, nside_chunk=128, **kwargs):
        from scipy.spatial import cKDTree as KDTree
        from desisim.templates import BGS
        from desiutil.sklearn import GaussianMixtureModel

        super(BGSMaker, self).__init__()

        self.seed = seed
        self.nside_chunk = nside_chunk
        self.objtype = 'BGS'

        if self.wave is None:
            BGSMaker.wave = _default_wave()
        if self.template_maker is None:
            BGSMaker.template_maker = BGS(wave=self.wave)
            
        self.meta = self.template_maker.basemeta

        if self.tree is None:
            zobj = self.meta['Z'].data
            mabs = self.meta['SDSS_UGRIZ_ABSMAG_Z01'].data
            rmabs = mabs[:, 2]
            gr = mabs[:, 1] - mabs[:, 2]
            BGSMaker.tree = KDTree(np.vstack((zobj, rmabs, gr)).T)

        if self.GMM_BGS is None:
            self.read_GMM(target='BGS')

        if self.GMM_nospectra is None:
            gmmfile = resource_filename('desitarget', 'mock/data/quicksurvey_gmm_bgs.fits')
            BGSMaker.GMM_nospectra = GaussianMixtureModel.load(gmmfile)

    def read(self, mockfile=None, mockformat='durham_mxxl_hdf5', healpixels=None,
             nside=None, magcut=None, only_coords=False, mock_density=False, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'durham_mxxl_hdf5'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        magcut : :class:`float`
            Magnitude cut (hard-coded to SDSS r-band) to subselect targets
            brighter than magcut. 
        only_coords : :class:`bool`, optional
            For various applications, only read the target coordinates.
        mock_density : :class:`bool`, optional
            Compute the median target density in the mock.  Defaults to False.

        Returns
        -------
        :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        if self.mockformat == 'durham_mxxl_hdf5':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'bgs', 'MXXL', 'desi_footprint', 'v0.0.4', 'BGS.hdf5')            
            MockReader = ReadMXXL()
        elif self.mockformat == 'gaussianfield':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'GaussianRandomField', 'v0.0.8_2LPT', 'BGS.fits')
            MockReader = ReadGaussianField()
        elif self.mockformat == 'bgs-gama':
            MockReader = ReadGAMA()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile
            
        data = MockReader.readmock(mockfile, target_name=self.objtype,
                                   healpixels=healpixels, nside=nside,
                                   magcut=magcut, only_coords=only_coords,
                                   mock_density=mock_density, seed=self.seed)

        return data

    def make_spectra(self, data=None, indx=None, seed=None, no_spectra=False):
        """Generate BGS spectra.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        no_spectra : :class:`bool`, optional
            Do not generate spectra.  Defaults to False.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        objtruth : :class:`astropy.table.Table`
            Corresponding objtype-specific truth table (if applicable).
        
        """
        if seed is None:
            seed = self.seed
        rand = np.random.RandomState(seed)

        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        if no_spectra:
            flux = []
            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            meta['SEED'][:] = rand.randint(2**31, size=nobj)
            meta['REDSHIFT'][:] = data['Z'][indx]
            self.sample_gmm_nospectra(meta, rand=rand) # noiseless photometry from pre-computed GMMs
        else:
            input_meta, _ = empty_metatable(nmodel=nobj, objtype=self.objtype)
            input_meta['SEED'][:] = rand.randint(2**31, size=nobj)
            input_meta['REDSHIFT'][:] = data['Z'][indx]
            
            vdisp = self._sample_vdisp(data['RA'][indx], data['DEC'][indx], mean=1.9,
                                       sigma=0.15, seed=seed, nside=self.nside_chunk)

            if self.mockformat == 'durham_mxxl_hdf5':
                input_meta['TEMPLATEID'][:] = self._query( np.vstack((
                    data['Z'][indx],
                    data['SDSS_absmag_r01'][indx],
                    data['SDSS_01gr'][indx])).T )

                input_meta['MAG'][:] = data['MAG'][indx]
                input_meta['MAGFILTER'][:] = data['MAGFILTER'][indx]

            elif self.mockformat == 'bgs-gama':
                # Could conceivably use other colors here--
                input_meta['TEMPLATEID'][:] = self._query( np.vstack((
                    data['Z'][indx],
                    data['RMABS_01'][indx],
                    data['GR_01'][indx])).T )

                input_meta['MAG'][:] = data['MAG'][indx]
                input_meta['MAGFILTER'][:] = data['MAGFILTER'][indx]

            elif self.mockformat == 'gaussianfield':
                # This is not quite right, but choose a template with equal probability.
                input_meta['TEMPLATEID'][:] = rand.choice(self.meta['TEMPLATEID'], nobj)
                input_meta['MAG'][:] = data['MAG'][indx]
                input_meta['MAGFILTER'][:] = data['MAGFILTER'][indx]
                
            # Build north/south spectra separately.
            south = np.where( data['SOUTH'][indx] == True )[0]
            north = np.where( data['SOUTH'][indx] == False )[0]

            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            flux = np.zeros([nobj, len(self.wave)], dtype='f4')

            for these, issouth in zip( (north, south), (False, True) ):
                if len(these) > 0:
                    flux1, _, meta1, objmeta1 = self.template_maker.make_templates(
                        input_meta=input_meta[these], vdisp=vdisp[these], south=issouth,
                        nocolorcuts=True)

                    meta[these] = meta1
                    objmeta[these] = objmeta1
                    flux[these, :] = flux1

        targets, truth, objtruth = self.populate_targets_truth(
            data, meta, objmeta, indx=indx, psf=False, seed=seed,
            truespectype='GALAXY', templatetype='BGS')

        return flux, self.wave, targets, truth, objtruth

    def select_targets(self, targets, truth, **kwargs):
        """Select BGS targets.  Input tables are modified in place.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        desi_target, bgs_target, mws_target = apply_cuts(targets, tcnames='BGS')
        
        targets['DESI_TARGET'] |= desi_target
        targets['BGS_TARGET'] |= bgs_target
        targets['MWS_TARGET'] |= mws_target
        
class STARMaker(SelectTargets):
    """Lower-level Class for preparing for stellar spectra to be generated,
    selecting standard stars, and selecting stars as contaminants for
    extragalactic targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.

    """
    wave, template_maker, tree = None, None, None
    star_maggies_g_north, star_maggies_r_north = None, None
    star_maggies_g_south, star_maggies_r_south = None, None
    
    def __init__(self, seed=None, **kwargs):
        from scipy.spatial import cKDTree as KDTree
        from speclite import filters
        from desisim.templates import STAR

        super(STARMaker, self).__init__()

        self.seed = seed
        self.objtype = 'STAR'

        if self.wave is None:
            STARMaker.wave = _default_wave()
        if self.template_maker is None:
            STARMaker.template_maker = STAR(wave=self.wave)

        self.meta = self.template_maker.basemeta

        # Pre-compute normalized synthetic photometry for the full set of
        # stellar templates.
        if (self.star_maggies_g_north is None or self.star_maggies_r_north is None or
            self.star_maggies_g_south is None or self.star_maggies_r_south is None):
            flux, wave = self.template_maker.baseflux, self.template_maker.basewave

            bassmzlswise = filters.load_filters('BASS-g', 'BASS-r', 'MzLS-z',
                                                'wise2010-W1', 'wise2010-W2')
            decamwise = filters.load_filters('decam2014-g', 'decam2014-r', 'decam2014-z',
                                             'wise2010-W1', 'wise2010-W2')
            maggies_north = bassmzlswise.get_ab_maggies(flux, wave, mask_invalid=True)
            maggies_south = decamwise.get_ab_maggies(flux, wave, mask_invalid=True)

            # Normalize to both sdss-g and sdss-r
            sdssg = filters.load_filters('sdss2010-g')
            sdssr = filters.load_filters('sdss2010-r')

            def _get_maggies(flux, wave, outmaggies, normfilter):
                normmaggies = normfilter.get_ab_maggies(flux, wave, mask_invalid=True)
                for filt, flux in zip( outmaggies.colnames, ('FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2') ):
                    outmaggies[filt] /= normmaggies[normfilter.names[0]]
                    outmaggies.rename_column(filt, flux)
                return outmaggies

            STARMaker.star_maggies_g_north = _get_maggies(flux, wave, maggies_north.copy(), sdssg)
            STARMaker.star_maggies_r_north = _get_maggies(flux, wave, maggies_north.copy(), sdssr)
            STARMaker.star_maggies_g_south = _get_maggies(flux, wave, maggies_south.copy(), sdssg)
            STARMaker.star_maggies_r_south = _get_maggies(flux, wave, maggies_south.copy(), sdssr)

        # Build the KD Tree.
        if self.tree is None:
            STARMaker.tree = KDTree(np.vstack(
                (self.meta['TEFF'].data,
                 self.meta['LOGG'].data,
                self.meta['FEH'].data)).T)
        
    def template_photometry(self, data=None, indx=None, rand=None, south=True):
        """Get stellar photometry from the templates themselves, by-passing the
        generation of spectra.

        """
        if rand is None:
            rand = np.random.RandomState()

        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)
        
        meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
        meta['SEED'][:] = rand.randint(2**31, size=nobj)
        meta['REDSHIFT'][:] = data['Z'][indx]
        meta['MAG'][:] = data['MAG'][indx]
        meta['MAGFILTER'][:] = data['MAGFILTER'][indx]
        
        objmeta['TEFF'][:] = data['TEFF'][indx]
        objmeta['LOGG'][:] = data['LOGG'][indx]
        objmeta['FEH'][:] = data['FEH'][indx]

        if self.mockformat == 'galaxia':
            templateid = self._query(np.vstack((data['TEFF'][indx],
                                                data['LOGG'][indx],
                                                data['FEH'][indx])).T)
        elif self.mockformat == 'mws_100pc':
            templateid = self._query(np.vstack((data['TEFF'][indx],
                                                data['LOGG'][indx],
                                                data['FEH'][indx])).T)

        normmag = 1e9 * 10**(-0.4 * data['MAG'][indx]) # nanomaggies

        # A little fragile -- assume that MAGFILTER is the same for all objects...
        if south:
            if data['MAGFILTER'][0] == 'sdss2010-g':
                star_maggies = self.star_maggies_g_south
            elif data['MAGFILTER'][0] == 'sdss2010-r':
                star_maggies = self.star_maggies_r_south
            else:
                log.warning('Unrecognized normalization filter {}!'.format(data['MAGFILTER'][0]))
                raise ValueError
        else:
            if data['MAGFILTER'][0] == 'sdss2010-g':
                star_maggies = self.star_maggies_g_north
            elif data['MAGFILTER'][0] == 'sdss2010-r':
                star_maggies = self.star_maggies_r_north
            else:
                log.warning('Unrecognized normalization filter {}!'.format(data['MAGFILTER'][0]))
                raise ValueError
            
        for key in ('FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2'):
            meta[key][:] = star_maggies[key][templateid] * normmag

        return meta, objmeta
 
    def select_contaminants(self, targets, truth):
        """Select stellar (faint and bright) contaminants for the extragalactic targets.
        Input tables are modified in place.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """ 
        from desitarget.cuts import isBGS_faint, isELG, isLRG_colors, isQSO_colors

        gflux, rflux, zflux, w1flux, w2flux = self.deredden(targets)

        # Select stellar contaminants for BGS_FAINT targets.
        bgs_faint = isBGS_faint(rflux=rflux)
        targets['BGS_TARGET'] |= (bgs_faint != 0) * self.bgs_mask.BGS_FAINT
        targets['BGS_TARGET'] |= (bgs_faint != 0) * self.bgs_mask.BGS_FAINT_SOUTH
        targets['DESI_TARGET'] |= (bgs_faint != 0) * self.desi_mask.BGS_ANY
        
        truth['CONTAM_TARGET'] |= (bgs_faint != 0) * self.contam_mask.BGS_IS_STAR
        truth['CONTAM_TARGET'] |= (bgs_faint != 0) * self.contam_mask.BGS_CONTAM

        # Select stellar contaminants for ELG targets.
        elg = isELG(gflux=gflux, rflux=rflux, zflux=zflux)
        targets['DESI_TARGET'] |= (elg != 0) * self.desi_mask.ELG
        targets['DESI_TARGET'] |= (elg != 0) * self.desi_mask.ELG_SOUTH
        
        truth['CONTAM_TARGET'] |= (elg != 0) * self.contam_mask.ELG_IS_STAR
        truth['CONTAM_TARGET'] |= (elg != 0) * self.contam_mask.ELG_CONTAM

        # Select stellar contaminants for LRG targets.
        lrg = isLRG_colors(gflux=gflux, rflux=rflux, zflux=zflux,
                           w1flux=w1flux, w2flux=w2flux)
        targets['DESI_TARGET'] |= (lrg != 0) * self.desi_mask.LRG
        targets['DESI_TARGET'] |= (lrg != 0) * self.desi_mask.LRG_SOUTH

        truth['CONTAM_TARGET'] |= (lrg != 0) * self.contam_mask.LRG_IS_STAR
        truth['CONTAM_TARGET'] |= (lrg != 0) * self.contam_mask.LRG_CONTAM

        # Select stellar contaminants for QSO targets.
        qso = isQSO_colors(gflux=gflux, rflux=rflux, zflux=zflux, w1flux=w1flux, 
                           w2flux=w2flux)
        targets['DESI_TARGET'] |= (qso != 0) * self.desi_mask.QSO
        targets['DESI_TARGET'] |= (qso != 0) * self.desi_mask.QSO_SOUTH

        truth['CONTAM_TARGET'] |= (qso != 0) * self.contam_mask.QSO_IS_STAR
        truth['CONTAM_TARGET'] |= (qso != 0) * self.contam_mask.QSO_CONTAM

class MWS_MAINMaker(STARMaker):
    """Read MWS_MAIN mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.
    calib_only : :class:`bool`, optional
        Use MWS_MAIN stars as calibration (standard star) targets, only.
        Defaults to False.

    """
    def __init__(self, seed=None, calib_only=False, **kwargs):
        super(MWS_MAINMaker, self).__init__()

        self.calib_only = calib_only

    def read(self, mockfile=None, mockformat='galaxia', healpixels=None,
             nside=None, nside_galaxia=8, magcut=None, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'galaxia'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        nside_galaxia : :class:`int`
            Healpixel nside indicating how the mock on-disk has been organized.
            Defaults to 8.

        Returns
        -------
        :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        if self.mockformat == 'galaxia':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'mws', 'galaxia', 'alpha', 'v0.0.5', 'healpix')
            MockReader = ReadGalaxia()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile
            
        data = MockReader.readmock(mockfile, target_name='MWS_MAIN',
                                   healpixels=healpixels, nside=nside,
                                   nside_galaxia=nside_galaxia, magcut=magcut)

        return data
    
    def make_spectra(self, data=None, indx=None, seed=None, no_spectra=False):
        """Generate MWS_MAIN stellar spectra.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        no_spectra : :class:`bool`, optional
            Do not generate spectra.  Defaults to False.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        
        """
        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        if seed is None:
            seed = self.seed
        rand = np.random.RandomState(seed)

        if no_spectra:
            flux = []
            meta, objmeta = self.template_photometry(data, indx, rand)
        else:
            input_meta = empty_metatable(nmodel=nobj, objtype=self.objtype, input_meta=True)
            input_meta['SEED'][:] = rand.randint(2**31, size=nobj)
            input_meta['REDSHIFT'][:] = data['Z'][indx]
            input_meta['MAG'][:] = data['MAG'][indx]
            input_meta['MAGFILTER'][:] = data['MAGFILTER'][indx]

            if self.mockformat == 'galaxia':
                input_meta['TEMPLATEID'][:] = self._query(
                    np.vstack((data['TEFF'][indx],
                               data['LOGG'][indx],
                               data['FEH'][indx])).T)

            # Build north/south spectra separately.
            south = np.where( data['SOUTH'][indx] == True )[0]
            north = np.where( data['SOUTH'][indx] == False )[0]
        
            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            flux = np.zeros([nobj, len(self.wave)], dtype='f4')

            for these, issouth in zip( (north, south), (False, True) ):
                if len(these) > 0:
                    # Note: no "nocolorcuts" argument!
                    flux1, _, meta1, objmeta1 = self.template_maker.make_templates(
                        input_meta=input_meta[these], south=issouth)

                    meta[these] = meta1
                    objmeta[these] = objmeta1
                    flux[these, :] = flux1

        targets, truth, objtruth = self.populate_targets_truth(
            data, meta, objmeta, indx=indx, psf=True, seed=seed,
            truespectype='STAR', templatetype='STAR')
                                                           
        return flux, self.wave, targets, truth, objtruth

    def select_targets(self, targets, truth):
        """Select various MWS stars and standard stars.  Input tables are modified in
        place.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        if self.calib_only:
            tcnames = 'STD'
        else:
            tcnames = ['MWS', 'STD']
            
        desi_target, bgs_target, mws_target = apply_cuts(targets, tcnames=tcnames)

        targets['DESI_TARGET'] |= targets['DESI_TARGET'] | desi_target
        targets['BGS_TARGET'] |= targets['BGS_TARGET'] | bgs_target
        targets['MWS_TARGET'] |= targets['MWS_TARGET'] | mws_target

        # Select bright stellar contaminants for the extragalactic targets.
        log.info('Temporarily turning off contaminants.')
        if False:
            self.select_contaminants(targets, truth)

class FAINTSTARMaker(STARMaker):
    """Read FAINTSTAR mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.
    calib_only : :class:`bool`, optional
        Use FAINTSTAR stars as calibration (standard star) targets and
        contaminants, only.  Defaults to True.

    """
    def __init__(self, seed=None, calib_only=True, **kwargs):
        super(FAINTSTARMaker, self).__init__()

    def read(self, mockfile=None, mockformat='galaxia', healpixels=None,
             nside=None, nside_galaxia=8, magcut=None, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'galaxia'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        nside_galaxia : :class:`int`
            Healpixel nside indicating how the mock on-disk has been organized.
            Defaults to 8.

        Returns
        -------
        :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        if self.mockformat == 'galaxia':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'mws', 'galaxia', 'alpha', '0.0.5_superfaint', 'healpix')
            MockReader = ReadGalaxia()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile
            
        data = MockReader.readmock(mockfile, target_name='FAINTSTAR',
                                   healpixels=healpixels, nside=nside,
                                   nside_galaxia=nside_galaxia, magcut=magcut)

        return data
    
    def make_spectra(self, data=None, indx=None, seed=None, no_spectra=False):
        """Generate FAINTSTAR stellar spectra.

        Note: These (numerous!) objects are only used as contaminants, so we use
        the templates themselves for the spectra rather than generating them
        on-the-fly.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        no_spectra : :class:`bool`, optional
            Do not generate spectra.  Defaults to False.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        objtruth : :class:`astropy.table.Table`
            Corresponding objtype-specific truth table (if applicable).

        """
        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        if seed is None:
            seed = self.seed
        rand = np.random.RandomState(seed)

        objseeds = rand.randint(2**31, size=nobj)

        if self.mockformat == 'galaxia':
            alldata = np.vstack((data['TEFF'][indx],
                                 data['LOGG'][indx],
                                 data['FEH'][indx])).T
            _, templateid = self._query(alldata)

        # Initialize dummy targets and truth tables.
        _targets = empty_targets_table(nobj)
        _truth = empty_truth_table(nobj)
        
        # Pack the noiseless stellar photometry in the truth table, generate
        # noisy photometry, and then select targets.
        normmag = 1e9 * 10**(-0.4 * data['MAG'][indx]) # nanomaggies

        if data['MAGFILTER'][0] == 'sdss2010-r':
            star_maggies = self.star_maggies_r
        elif data['MAGFILTER'][0] == 'sdss2010-g':
            star_maggies = self.star_maggies_g
        else:
            log.warning('Unrecognized normalization filter!')
            raise ValueError
        
        for key in ('FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2'):
            _truth[key][:] = star_maggies[key][templateid] * normmag

        for band in ('G', 'R', 'Z', 'W1', 'W2'):
            for prefix in ('MW_TRANSMISSION', 'PSFDEPTH'):
                key = '{}_{}'.format(prefix, band)
                _targets[key][:] = data[key][indx]

        self.scatter_photometry(data, _truth, _targets, indx=indx, psf=True, qaplot=False)

        self.select_targets(_targets, _truth)

        keep = np.where(_targets['DESI_TARGET'] != 0)[0]
        log.debug('Pre-selected {} FAINTSTAR targets.'.format(len(keep)))

        if len(keep) > 0:
            input_meta, objmeta = empty_metatable(nmodel=len(keep), objtype=self.objtype)
            input_meta['SEED'][:] = objseeds[keep]
            input_meta['REDSHIFT'][:] = data['Z'][indx][keep]
            input_meta['MAG'][:] = data['MAG'][indx][keep]
            
            objmeta['TEFF'][:] = data['TEFF'][indx][keep]
            objmeta['LOGG'][:] = data['LOGG'][indx][keep]
            objmeta['FEH'][:] = data['FEH'][indx][keep]

            if no_spectra:
                flux = []
                meta = input_meta
                targets, truth = self.populate_targets_truth(
                    data, meta, objmeta, indx=indx[keep], psf=True,
                    seed=seed, truespectype='STAR', templatetype='STAR')
            else:
                input_meta['TEMPLATEID'][:] = templateid[keep]

                # Note! No colorcuts.
                flux, _, meta, objmeta = self.template_maker.make_templates(input_meta=input_meta)

                # Force consistency in the noisy photometry so we select the same targets. 
                targets, truth, objtruth = self.populate_targets_truth(
                    data, meta, objmeta, indx=indx[keep], psf=True,
                    seed=seed, truespectype='STAR', templatetype='STAR')
                
                for filt in ('FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2'):
                    targets[filt][:] = _targets[filt][keep]

            self.select_targets(targets, truth)

            return flux, self.wave, targets, truth, objtruth

        else:
            return [], self.wave, None, [], [], []
                                                           
    def select_targets(self, targets, truth):
        """Select faint stellar contaminants for the extragalactic targets.  Input
        tables are modified in place.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        log.info('Temporarily turning off contaminants.')
        if False:
            self.select_contaminants(targets, truth)

class MWS_NEARBYMaker(STARMaker):
    """Read MWS_NEARBY mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.

    """
    def __init__(self, seed=None, **kwargs):
        super(MWS_NEARBYMaker, self).__init__()

    def read(self, mockfile=None, mockformat='mws_100pc', healpixels=None,
             nside=None, mock_density=False, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'mws_100pc'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        mock_density : :class:`bool`, optional
            Compute the median target density in the mock.  Defaults to False.

        Returns
        -------
        :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        if self.mockformat == 'mws_100pc':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'mws', '100pc', 'v0.0.3', 'mock_100pc.fits')
            MockReader = ReadMWS_NEARBY()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile

        data = MockReader.readmock(mockfile, target_name='MWS_NEARBY',
                                   healpixels=healpixels, nside=nside,
                                   mock_density=mock_density)

        return data
    
    def make_spectra(self, data=None, indx=None, seed=None, no_spectra=False):
        """Generate MWS_NEARBY stellar spectra.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        no_spectra : :class:`bool`, optional
            Do not generate spectra.  Defaults to False.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        
        """
        if seed is None:
            seed = self.seed
        rand = np.random.RandomState(seed)
        
        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        if no_spectra:
            flux = []
            meta, objmeta = self.template_photometry(data, indx, rand)
        else:
            input_meta = empty_metatable(nmodel=nobj, objtype=self.objtype, input_meta=True)
            input_meta['SEED'][:] = rand.randint(2**31, size=nobj)
            input_meta['REDSHIFT'][:] = data['Z'][indx]
            input_meta['MAG'][:] = data['MAG'][indx]
            input_meta['MAGFILTER'][:] = data['MAGFILTER'][indx]

            if self.mockformat == 'mws_100pc':
                input_meta['TEMPLATEID'][:] = self._query(
                    np.vstack((data['TEFF'][indx],
                               data['LOGG'][indx],
                               data['FEH'][indx])).T)

            # Build north/south spectra separately.
            south = np.where( data['SOUTH'][indx] == True )[0]
            north = np.where( data['SOUTH'][indx] == False )[0]
        
            meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            flux = np.zeros([nobj, len(self.wave)], dtype='f4')

            for these, issouth in zip( (north, south), (False, True) ):
                if len(these) > 0:
                    # Note: no "nocolorcuts" argument!
                    flux1, _, meta1, objmeta1 = self.template_maker.make_templates(
                        input_meta=input_meta[these], south=issouth)

                    meta[these] = meta1
                    objmeta[these] = objmeta1
                    flux[these, :] = flux1

        targets, truth, objtruth = self.populate_targets_truth(
            data, meta, objmeta, indx=indx, psf=True, seed=seed,
            truespectype='STAR', templatetype='STAR',
            templatesubtype=data['TEMPLATESUBTYPE'][indx])

        return flux, self.wave, targets, truth, objtruth

    def select_targets(self, targets, truth, **kwargs):
        """Select MWS_NEARBY targets.  Input tables are modified in place.

        Note: The selection here eventually will be done with Gaia (I think) so
        for now just do a "perfect" selection.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        if False:
            desi_target, bgs_target, mws_target = apply_cuts(targets, tcnames=['MWS'])
        else:
            log.warning('Applying ad hoc selection of MWS_NEARBY targets (no Gaia in mocks).')

            mws_nearby = np.ones(len(targets)) # select everything!
            #mws_nearby = (truth['MAG'] <= 20.0) * 1 # SDSS g-band!

            desi_target = (mws_nearby != 0) * self.desi_mask.MWS_ANY
            mws_target = (mws_nearby != 0) * self.mws_mask.mask('MWS_NEARBY')

            targets['DESI_TARGET'] |= desi_target
            targets['MWS_TARGET'] |= mws_target

class WDMaker(SelectTargets):
    """Read WD mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.
    calib_only : :class:`bool`, optional
        Use WDs as calibration (standard star) targets, only.  Defaults to False. 

    """
    wave, da_template_maker, db_template_maker = None, None, None
    tree_da, tree_db = None, None
    wd_maggies_da_north, wd_maggies_da_north = None, None
    wd_maggies_db_south, wd_maggies_db_south = None, None

    def __init__(self, seed=None, calib_only=False, **kwargs):
        from scipy.spatial import cKDTree as KDTree
        from speclite import filters 
        from desisim.templates import WD
        
        super(WDMaker, self).__init__()

        self.seed = seed
        self.objtype = 'WD'
        self.calib_only = calib_only

        if self.wave is None:
            WDMaker.wave = _default_wave()
            
        if self.da_template_maker is None:
            WDMaker.da_template_maker = WD(wave=self.wave, subtype='DA')
            
        if self.db_template_maker is None:
            WDMaker.db_template_maker = WD(wave=self.wave, subtype='DB')
        
        self.meta_da = self.da_template_maker.basemeta
        self.meta_db = self.db_template_maker.basemeta

        # Pre-compute normalized synthetic photometry for the full set of DA and
        # DB templates.
        if (self.wd_maggies_da_north is None or self.wd_maggies_da_south is None or
            self.wd_maggies_db_north is None or self.wd_maggies_db_south is None):

            wave = self.da_template_maker.basewave
            flux_da, flux_db = self.da_template_maker.baseflux, self.db_template_maker.baseflux

            bassmzlswise = filters.load_filters('BASS-g', 'BASS-r', 'MzLS-z',
                                                'wise2010-W1', 'wise2010-W2')
            decamwise = filters.load_filters('decam2014-g', 'decam2014-r', 'decam2014-z',
                                             'wise2010-W1', 'wise2010-W2')

            maggies_da_north = decamwise.get_ab_maggies(flux_da, wave, mask_invalid=True)
            maggies_db_north = decamwise.get_ab_maggies(flux_db, wave, mask_invalid=True)
            maggies_da_south = bassmzlswise.get_ab_maggies(flux_da, wave, mask_invalid=True)
            maggies_db_south = bassmzlswise.get_ab_maggies(flux_db, wave, mask_invalid=True)

            # Normalize to sdss-g
            normfilter = filters.load_filters('sdss2010-g')
            def _get_maggies(flux, wave, outmaggies, normfilter):
                normmaggies = normfilter.get_ab_maggies(flux, wave, mask_invalid=True)
                for filt, flux in zip( outmaggies.colnames, ('FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2') ):
                    outmaggies[filt] /= normmaggies[normfilter.names[0]]
                    outmaggies.rename_column(filt, flux)
                return outmaggies

            WDMaker.wd_maggies_da_north = _get_maggies(flux_da, wave, maggies_da_north.copy(), normfilter)
            WDMaker.wd_maggies_da_south = _get_maggies(flux_da, wave, maggies_da_south.copy(), normfilter)
            WDMaker.wd_maggies_db_north = _get_maggies(flux_db, wave, maggies_db_north.copy(), normfilter)
            WDMaker.wd_maggies_db_south = _get_maggies(flux_db, wave, maggies_db_south.copy(), normfilter)

        # Build the KD Trees
        if self.tree_da is None:
            WDMaker.tree_da = KDTree(np.vstack((self.meta_da['TEFF'].data,
                                                self.meta_da['LOGG'].data)).T)
        if self.tree_db is None:
            WDMaker.tree_db = KDTree(np.vstack((self.meta_db['TEFF'].data,
                                                self.meta_db['LOGG'].data)).T)

    def read(self, mockfile=None, mockformat='mws_wd', healpixels=None,
             nside=None, mock_density=False, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'mws_wd'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        mock_density : :class:`bool`, optional
            Compute the median target density in the mock.  Defaults to False.

        Returns
        -------
        :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        if self.mockformat == 'mws_wd':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'mws', 'wd', 'v0.0.2', 'mock_wd.fits')
            MockReader = ReadMWS_WD()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile

        data = MockReader.readmock(mockfile, target_name=self.objtype,
                                   healpixels=healpixels, nside=nside,
                                   mock_density=mock_density)

        return data

    def wd_template_photometry(self, data=None, indx=None, rand=None,
                               subtype='DA', south=True):
        """Get stellar photometry from the templates themselves, by-passing the
        generation of spectra.

        """
        if rand is None:
            rand = np.random.RandomState()

        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)
        
        meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
        meta['SEED'][:] = rand.randint(2**31, size=nobj)
        meta['REDSHIFT'][:] = data['Z'][indx]
        meta['MAG'][:] = data['MAG'][indx]
        meta['MAGFILTER'][:] = data['MAGFILTER'][indx]
        meta['SUBTYPE'][:] = data['TEMPLATESUBTYPE'][indx]

        objmeta['TEFF'][:] = data['TEFF'][indx]
        objmeta['LOGG'][:] = data['LOGG'][indx]

        if self.mockformat == 'mws_wd':
            templateid = self._query(
                np.vstack((data['TEFF'][indx],
                           data['LOGG'][indx])).T, subtype=subtype)

        normmag = 1e9 * 10**(-0.4 * data['MAG'][indx]) # nanomaggies

        if south:
            if subtype == 'DA':
                wd_maggies = self.wd_maggies_da_south
            elif subtype == 'DB':
                wd_maggies = self.wd_maggies_db_south
            else:
                log.warning('Unrecognized subtype {}!'.format(subtype))
                raise ValueError
        else:
            if subtype == 'DA':
                wd_maggies = self.wd_maggies_da_north
            elif subtype == 'DB':
                wd_maggies = self.wd_maggies_db_north
            else:
                log.warning('Unrecognized subtype {}!'.format(subtype))
                raise ValueError
            
        for key in ('FLUX_G', 'FLUX_R', 'FLUX_Z', 'FLUX_W1', 'FLUX_W2'):
            meta[key][:] = wd_maggies[key][templateid] * normmag

        return meta, objmeta

    def make_spectra(self, data=None, indx=None, seed=None, no_spectra=False):
        """Generate WD spectra, dealing with DA vs DB white dwarfs separately.
        
        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.
        no_spectra : :class:`bool`, optional
            Do not generate spectra.  Defaults to False.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        if seed is None:
            seed = self.seed
        rand = np.random.RandomState(seed)
        
        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        if self.mockformat == 'mws_wd':
            if no_spectra:
                flux = []
                meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
            else:
                input_meta = empty_metatable(nmodel=nobj, objtype=self.objtype, input_meta=True)
                input_meta['SEED'][:] = rand.randint(2**31, size=nobj)
                input_meta['REDSHIFT'][:] = data['Z'][indx]
                input_meta['MAG'][:] = data['MAG'][indx]
                input_meta['MAGFILTER'][:] = data['MAGFILTER'][indx]

                meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
                flux = np.zeros([nobj, len(self.wave)], dtype='f4')

            allsubtype = data['TEMPLATESUBTYPE'][indx]
            for subtype in ('DA', 'DB'):
                match = np.where(allsubtype == subtype)[0]
                if len(match) > 0:
                    if not no_spectra:
                        input_meta['TEMPLATEID'][match] = self._query(
                            np.vstack((data['TEFF'][indx][match],
                                       data['LOGG'][indx][match])).T,
                            subtype=subtype)

                    # Build north/south spectra separately.
                    south = np.where( data['SOUTH'][indx][match] == True )[0]
                    north = np.where( data['SOUTH'][indx][match] == False )[0]

                    for these, issouth in zip( (north, south), (False, True) ):
                        if len(these) > 0:
                            if no_spectra:
                                meta1, objmeta1 = self.wd_template_photometry(
                                    data, indx[match][these], rand, subtype,
                                    south=issouth)
                                meta[match][these] = meta1
                                objmeta[match][these] = objmeta1
                            else:
                                # Note: no "nocolorcuts" argument!
                                template_maker = getattr(self, '{}_template_maker'.format(subtype.lower()))
                                flux1, _, meta1, objmeta1 = template_maker.make_templates(
                                    input_meta=input_meta[match][these], south=issouth)

                                meta[match[these]] = meta1
                                objmeta[match[these]] = objmeta1
                                flux[match[these], :] = flux1

        targets, truth, objtruth = self.populate_targets_truth(
            data, meta, objmeta, indx=indx, psf=True, seed=seed,
            truespectype='WD', templatetype='WD',
            templatesubtype=allsubtype)

        return flux, self.wave, targets, truth, objtruth

    def select_targets(self, targets, truth, **kwargs):
        """Select MWS_WD targets and STD_WD standard stars.  Input tables are modified
        in place.

        Note: The selection here eventually will be done with Gaia (I think) so
        for now just do a "perfect" selection.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        if not self.calib_only:
            if False:
                desi_target, bgs_target, mws_target = apply_cuts(targets, tcnames=['MWS'])
            else:
                log.warning('Applying ad hoc selection of MWS_WD targets (no Gaia in mocks).')

                #mws_wd = np.ones(len(targets)) # select everything!
                mws_wd = ((truth['MAG'] >= 15.0) * (truth['MAG'] <= 20.0)) * 1 # SDSS g-band!

                desi_target = (mws_wd != 0) * self.desi_mask.MWS_ANY
                mws_target = (mws_wd != 0) * self.mws_mask.mask('MWS_WD')

                targets['DESI_TARGET'] |= desi_target
                targets['MWS_TARGET'] |= mws_target

        if False:
            desi_target, bgs_target, mws_target = apply_cuts(targets, tcnames=['STD'])
            targets['DESI_TARGET'] |= desi_target
        else:
            log.warning('Applying ad hoc selection of STD_WD targets (no Gaia in mocks).')
            
            # Ad hoc selection of WD standards using just on g-band magnitude (not
            # TEMPLATESUBTYPE!)
            std_wd = (truth['MAG'] <= 19.0) * 1 # SDSS g-band!
            targets['DESI_TARGET'] |= (std_wd !=0) * self.desi_mask.mask('STD_WD')

class SKYMaker(SelectTargets):
    """Read SKY mocks, generate spectra, and select targets.

    Parameters
    ----------
    seed : :class:`int`, optional
        Seed for reproducibility and random number generation.

    """
    wave = None
    
    def __init__(self, seed=None, **kwargs):
        super(SKYMaker, self).__init__()

        self.seed = seed
        self.objtype = 'SKY'

        if self.wave is None:
            SKYMaker.wave = _default_wave()
        
    def read(self, mockfile=None, mockformat='uniformsky', healpixels=None,
             nside=None, mock_density=False, **kwargs):
        """Read the catalog.

        Parameters
        ----------
        mockfile : :class:`str`
            Full path to the mock catalog to read.
        mockformat : :class:`str`
            Mock catalog format.  Defaults to 'gaussianfield'.
        healpixels : :class:`int`
            Healpixel number to read.
        nside : :class:`int`
            Healpixel nside corresponding to healpixels.
        mock_density : :class:`bool`, optional
            Compute the median target density in the mock.  Defaults to False.

        Returns
        -------
        :class:`dict`
            Dictionary of target properties with various keys (to be documented). 

        Raises
        ------
        ValueError
            If mockformat is not recognized.

        """
        self.mockformat = mockformat.lower()
        if self.mockformat == 'uniformsky':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'uniformsky', '0.1', 'uniformsky-2048-0.1.fits')
            MockReader = ReadUniformSky()
        elif self.mockformat == 'gaussianfield':
            self.default_mockfile = os.path.join(
                os.getenv('DESI_ROOT'), 'mocks', 'GaussianRandomField', '0.0.1', '2048', 'random.fits')
            MockReader = ReadGaussianField()
        else:
            log.warning('Unrecognized mockformat {}!'.format(mockformat))
            raise ValueError

        if mockfile is None:
            mockfile = self.default_mockfile

        data = MockReader.readmock(mockfile, target_name=self.objtype,
                                   healpixels=healpixels, nside=nside,
                                   mock_density=mock_density)

        return data

    def make_spectra(self, data=None, indx=None, seed=None, **kwargs):
        """Generate SKY spectra.

        Parameters
        ----------
        data : :class:`dict`
            Dictionary of source properties.
        indx : :class:`numpy.ndarray`, optional
            Generate spectra for a subset of the objects in the data dictionary,
            as specified using their zero-indexed indices.
        seed : :class:`int`, optional
            Seed for reproducibility and random number generation.

        Returns
        -------
        flux : :class:`numpy.ndarray`
            Target spectra.
        wave : :class:`numpy.ndarray`
            Corresponding wavelength array.
        meta : :class:`astropy.table.Table`
            Spectral metadata table.
        targets : :class:`astropy.table.Table`
            Target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.
        objtruth : :class:`astropy.table.Table`
            Corresponding objtype-specific truth table (if applicable).
        
        """
        if seed is None:
            seed = self.seed
        rand = np.random.RandomState(seed)

        if indx is None:
            indx = np.arange(len(data['RA']))
        nobj = len(indx)

        meta, objmeta = empty_metatable(nmodel=nobj, objtype=self.objtype)
        meta['SEED'][:] = rand.randint(2**31, size=nobj)
        meta['REDSHIFT'][:] = data['Z'][indx]
        
        flux = np.zeros((nobj, len(self.wave)), dtype='i1')
        targets, truth, objtruth = self.populate_targets_truth(
            data, meta, objmeta, indx=indx, psf=False, seed=seed,
            truespectype='SKY', templatetype='SKY')

        return flux, self.wave, targets, truth, objtruth

    def select_targets(self, targets, truth, **kwargs):
        """Select SKY targets (i.e., everything).  Input tables are modified in place.

        Parameters
        ----------
        targets : :class:`astropy.table.Table`
            Input target catalog.
        truth : :class:`astropy.table.Table`
            Corresponding truth table.

        """
        targets['DESI_TARGET'] |= self.desi_mask.mask('SKY')
