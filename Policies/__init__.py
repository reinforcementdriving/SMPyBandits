# -*- coding: utf-8 -*-
""" Policies : contains various bandits algorithms:

- "Stupid" algorithms: Uniform, UniformOnSome, TakeFixedArm, TakeRandomFixedArm

- Greedy algorithms: EpsilonGreedy, EpsilonFirst, EpsilonDecreasing

- Probabilistic weighting algorithms: Softmax, SoftmaxDecreasing, SoftMix, SoftmaxWithHorizon, Exp3, Exp3Decreasing, Exp3SoftMix, Exp3WithHorizon

- Index based algorithms: EmpiricalMeans, UCB, UCBlog10, UCBwrong, UCBlog10alpha, UCBalpha, UCBmin, UCBplus, UCBrandomInit, UCBV, UCBVtuned, MOSS, MOSSH

- Bayesian algorithms: Thompson, BayesUCB

- Based on Kullback-Leibler divergence: klUCB, klUCBlog10, klUCBloglog, klUCBloglog10, klUCBPlus, klUCBHPlus, klUCBPlusPlus

- Empirical KL-UCB algorithm: KLempUCB

- Hybrids algorithms: AdBandit

- Aggregation algorithms: Aggr

- Designed for (fully decentralized) multi-player games: MusicalChair, MEGA
"""

__author__ = "Lilian Besson"
__version__ = "0.6"

# --- Mine, uniform ones or fixed arm / fixed subset ones
from .Uniform import Uniform
from .UniformOnSome import UniformOnSome
from .TakeFixedArm import TakeFixedArm
from .TakeRandomFixedArm import TakeRandomFixedArm

# --- Mine, simple exploratory policies
from .EpsilonGreedy import EpsilonGreedy
from .EpsilonFirst import EpsilonFirst
# --- Mine, simple exploratory policies
from .EpsilonDecreasing import EpsilonDecreasing
from .EpsilonDecreasingMEGA import EpsilonDecreasingMEGA
from .EpsilonExpDecreasing import EpsilonExpDecreasing
from .EmpiricalMeans import EmpiricalMeans

# --- Mine, Softmax and Exp3 policies
from .Softmax import Softmax, SoftmaxDecreasing, SoftMix, SoftmaxWithHorizon
from .Exp3 import Exp3, Exp3Decreasing, Exp3SoftMix, Exp3WithHorizon

# --- Simple UCB policies
from .UCB import UCB
from .UCBlog10 import UCBlog10  # With log10(t) instead of log(t) = ln(t)
from .UCBwrong import UCBwrong  # With a volontary typo!
from .UCBalpha import UCBalpha  # Different indexes
from .UCBlog10alpha import UCBlog10alpha  # Different indexes
from .UCBmin import UCBmin      # Different indexes
from .UCBplus import UCBplus    # Different indexes
from .UCBrandomInit import UCBrandomInit

# --- UCB policies with variance terms
from .UCBV import UCBV          # Different indexes
from .UCBVtuned import UCBVtuned  # Different indexes

# --- MOSS index policy
from .MOSS import MOSS
from .MOSSH import MOSSH  # Knowing the horizon

# --- Thompson sampling index policy
from .Thompson import Thompson

# --- Bayesian index policy
from .BayesUCB import BayesUCB

# --- Kullback-Leibler based index policy
from .klUCB import klUCB
from .klUCBlog10 import klUCBlog10  # With log10(t) instead of log(t) = ln(t)
from .klUCBloglog import klUCBloglog  # With log(t) + c log(log(t)) and c = 1 (variable)
from .klUCBloglog10 import klUCBloglog10  # With log10(t) + c log10(log10(t)) and c = 1 (variable)
from .klUCBPlus import klUCBPlus    # Different indexes
from .klUCBHPlus import klUCBHPlus  # Different indexes
from .klUCBPlusPlus import klUCBPlusPlus  # Different indexes
from .KLempUCB import KLempUCB  # Empirical KL UCB

# From https://github.com/flaviotruzzi/AdBandits/
from .AdBandits import AdBandits

# --- Mine, aggregated ones, like Exp4  FIXME give it a better name!
from .Aggr import Aggr


# --- Mine, implemented from state-of-the-art papers on multi-player policies

from .MusicalChair import MusicalChair  # Cf. [Shamir et al., 2015](https://arxiv.org/abs/1512.02866)
# from .DynamicMusicalChair import DynamicMusicalChair  # FIXME write it! Can be just a subclass of MusicalChair

from .MEGA import MEGA  # Cf. [Avner & Mannor, 2014](https://arxiv.org/abs/1404.5421)


# --- KL-UCB index functions
from .usenumba import jit

from .kullback import klucbBern, klucbExp, klucbGauss, klucbPoisson, klucbGamma

klucb_mapping = {
    "Bernoulli": klucbBern,
    "Exponential": klucbExp,
    "Gaussian": klucbGauss,
    "Poisson": klucbPoisson,
    "Gamma": klucbGamma,
}
