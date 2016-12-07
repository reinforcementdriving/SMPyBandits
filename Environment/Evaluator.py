# -*- coding: utf-8 -*-
""" Evaluator class to wrap and run the simulations."""
from __future__ import print_function

__author__ = "Lilian Besson"
__version__ = "0.2"

# Generic imports
from copy import deepcopy
from random import shuffle
# Scientific imports
import numpy as np
import matplotlib.pyplot as plt
try:
    import joblib
    USE_JOBLIB = True
except ImportError:
    print("joblib not found. Install it from pypi ('pip install joblib') or conda.")
    USE_JOBLIB = False
# Local imports
from .plotsettings import DPI, signature, maximizeWindow, palette, makemarkers
from .Result import Result
from .MAB import MAB


# Parameters for the random events
random_shuffle = False
random_invert = False
nb_random_events = 4


class Evaluator(object):
    """ Evaluator class to run the simulations."""

    def __init__(self, configuration,
                 finalRanksOnAverage=True, averageOn=5e-3,
                 useJoblibForPolicies=False):
        # Configuration
        self.cfg = configuration
        # Attributes
        self.nbPolicies = len(self.cfg['policies'])
        print("Number of policies in this comparaison:", self.nbPolicies)
        self.horizon = self.cfg['horizon']
        print("Time horizon:", self.horizon)
        self.repetitions = self.cfg['repetitions']
        print("Number of repetitions:", self.repetitions)
        # Flags
        self.finalRanksOnAverage = finalRanksOnAverage
        self.averageOn = averageOn
        self.useJoblibForPolicies = useJoblibForPolicies
        self.useJoblib = USE_JOBLIB and self.cfg['n_jobs'] != 1
        # Internal object memory
        self.envs = []
        self.policies = []
        self.__initEnvironments__()
        # Internal vectorial memory
        self.rewards = np.zeros((self.nbPolicies, len(self.envs), self.horizon))
        self.rewardsSquared = np.zeros((self.nbPolicies, len(self.envs), self.horizon))
        self.BestArmPulls = dict()
        self.pulls = dict()
        for env in range(len(self.envs)):
            self.BestArmPulls[env] = np.zeros((self.nbPolicies, self.horizon))
            self.pulls[env] = np.zeros((self.nbPolicies, self.envs[env].nbArms))
        print("Number of environments to try:", len(self.envs))

    def __initEnvironments__(self):
        for armType in self.cfg['environment']:
            self.envs.append(MAB(armType))

    def __initPolicies__(self, env):
        for policyId, policy in enumerate(self.cfg['policies']):
            print("- Adding policy #{} = {} ...".format(policyId + 1, policy))  # DEBUG
            if isinstance(policy, dict):
                print("  Creating this policy from a dictionnary 'self.cfg['policies'][{}]' = {} ...".format(policyId, policy))  # DEBUG
                self.policies.append(policy['archtype'](env.nbArms, **policy['params']))
            else:
                print("  Using this already created policy 'self.cfg['policies'][{}]' = {} ...".format(policyId, policy))  # DEBUG
                self.policies.append(policy)

    def start_all_env(self):
        for envId, env in enumerate(self.envs):
            self.start_one_env(envId, env)

    # @profile  # DEBUG with kernprof (cf. https://github.com/rkern/line_profiler#kernprof
    def start_one_env(self, envId, env):
        print("\nEvaluating environment:", repr(env))
        self.policies = []
        self.__initPolicies__(env)
        for policyId, policy in enumerate(self.policies):
            print("\n- Evaluating policy #{}/{}: {} ...".format(policyId + 1, self.nbPolicies, policy))
            if self.useJoblib:
                results = joblib.Parallel(n_jobs=self.cfg['n_jobs'], verbose=self.cfg['verbosity'])(
                    joblib.delayed(delayed_play)(env, policy, self.horizon)
                    for _ in range(self.repetitions)
                )
            else:
                results = []
                for _ in range(self.repetitions):
                    r = delayed_play(env, policy, self.horizon)
                    results.append(r)
            # Get the position of the best arms
            means = np.array([arm.mean() for arm in env.arms])
            bestarm = np.max(means)
            index_bestarm = np.argwhere(np.isclose(means, bestarm))
            # Store the results
            for r in results:
                self.rewards[policyId, envId, :] += r.rewards
                self.rewardsSquared[policyId, envId, :] += r.rewardsSquared
                self.BestArmPulls[envId][policyId, :] += np.cumsum(np.in1d(r.choices, index_bestarm))
                self.pulls[envId][policyId, :] += r.pulls

    def getPulls(self, policyId, environmentId=0):
        return self.pulls[environmentId][policyId, :] / float(self.repetitions)

    def getBestArmPulls(self, policyId, environmentId=0):
        # We have to divide by a arange() = cumsum(ones) to get a frequency
        return self.BestArmPulls[environmentId][policyId, :] / (float(self.repetitions) * np.arange(start=1, stop=1 + self.horizon))

    def getRewards(self, policyId, environmentId=0):
        return self.rewards[policyId, environmentId, :] / float(self.repetitions)

    def getCumulatedRegret(self, policyId, environmentId=0):
        # return np.arange(1, 1 + self.horizon) * self.envs[environmentId].maxArm - np.cumsum(self.getRewards(policyId, environmentId))
        return np.cumsum(self.envs[environmentId].maxArm - self.getRewards(policyId, environmentId))

    def getAverageRewards(self, policyId, environmentId=0):
        return np.cumsum(self.getRewards(policyId, environmentId)) / np.arange(1, 1 + self.horizon)

    def getRewardsSquared(self, policyId, environmentId=0):
        return self.rewardsSquared[policyId, environmentId, :] / float(self.repetitions)

    def getSTDRegret(self, policyId, environmentId=0, averageRegret=False):
        X = np.arange(1, 1 + self.horizon)
        Y = self.getRewards(policyId, environmentId)
        Y2 = self.getRewardsSquared(policyId, environmentId)
        if averageRegret:  # FIXME The expectation is also done on time ??
            Ycum2 = (np.cumsum(Y) / X)**2
            Y2cum = np.cumsum(Y2) / X
            assert np.all(Y2cum >= Ycum2), "Error: getSTDRegret found a nan value in the standard deviation (ie a point where Y2cum < Ycum2)."
            stdY = np.sqrt(Y2cum - Ycum2)
            # stdY /= 10  # XXX make it look smaller????
            stdY /= 10 * np.max(Y)
        else:  # FIXED The expectation was done on nb of repetitions
            # https://en.wikipedia.org/wiki/Algebraic_formula_for_the_variance#In_terms_of_raw_moments
            # std(Y) = sqrt( E[Y**2] - E[Y]**2 )
            stdY = np.sqrt(Y2 - Y**2)
            # stdY /= 10  # XXX make it look smaller????
            stdY = np.cumsum(stdY)  # cumsum is needed here??
            stdY /= 0.1 * np.max(Y)
        print("  - stdY =", stdY)  # DEBUG
        print("  - np.shape(stdY) =", np.shape(stdY))  # DEBUG
        print("  - np.min(stdY) =", np.min(stdY))  # DEBUG
        print("  - np.max(stdY) =", np.max(stdY))  # DEBUG
        return stdY

    def plotRegrets(self, environmentId,
                    savefig=None, averageRegret=False, errorplot=True, semilogx=False, normalizedRegret=False
                    ):
        plt.figure()
        ymin = 0
        colors = palette(self.nbPolicies)
        markers = makemarkers(self.nbPolicies)
        markers_on = np.arange(0, self.horizon, int(self.horizon / 10.0))
        delta_marker = 1 + int(self.horizon / 200.0)  # XXX put back 0 if needed
        X = np.arange(self.horizon)
        for i, policy in enumerate(self.policies):
            if averageRegret:
                Y = self.getAverageRewards(i, environmentId)
            else:
                Y = self.getCumulatedRegret(i, environmentId)
                if normalizedRegret:
                    Y /= np.log(2 + X)   # FIXME better way to prevent /0 ??
            ymin = min(ymin, np.min(Y))
            if semilogx:
                plt.semilogx(Y, label=str(policy), color=colors[i], marker=markers[i], markevery=(delta_marker * (i % self.envs[environmentId].nbArms) + markers_on))
            else:
                plt.plot(Y, label=str(policy), color=colors[i], marker=markers[i], markevery=(delta_marker * (i % self.envs[environmentId].nbArms) + markers_on))
            # XXX plt.fill_between http://matplotlib.org/users/recipes.html#fill-between-and-alpha instead of plt.errorbar
            if errorplot and self.repetitions > 1:
                stdY = self.getSTDRegret(i, environmentId, averageRegret=averageRegret)
                # stdY = 0.01 * np.max(np.abs(Y))  # DEBUG: 1% std to see it
                plt.fill_between(X, Y - stdY, Y + stdY, facecolor=colors[i], alpha=0.3)
                # plt.errorbar(X, Y, yerr=stdY, label=str(policy), color=colors[i], marker=markers[i], markevery=(delta_marker * (i % self.envs[environmentId].nbArms) + markers_on), alpha=0.9)
        plt.xlabel(r"Time steps $t = 1 .. T$, horizon $T = {}$".format(self.horizon))
        ymax = max(plt.ylim()[1], 1)
        plt.ylim(ymin, ymax)
        if averageRegret:
            plt.legend(loc='center right', numpoints=1, fancybox=True, framealpha=0.7)  # http://matplotlib.org/users/recipes.html#transparent-fancy-legends
            plt.ylabel(r"Mean Reward, average on time $\tilde{r}_t = \frac{1}{t} \sum_{s = 1}^{t} \mathbb{E}_{%d}[r_s]$" % (self.repetitions,))
            plt.title("Mean Reward for different bandit algorithms, averaged ${}$ times\nArms: ${}${}".format(self.repetitions, repr(self.envs[environmentId].arms), signature))
        elif normalizedRegret:
            plt.legend(loc='upper left', numpoints=1, fancybox=True, framealpha=0.7)  # http://matplotlib.org/users/recipes.html#transparent-fancy-legends
            plt.ylabel(r"Normalized Cumulated Regret $\frac{R_t}{\log t} = \frac{t}{\log t} \mu^* - \frac{1}{\log t}\sum_{s = 1}^{t} \mathbb{E}_{%d}[r_s]$" % (self.repetitions,))
            plt.title("Normalized Cumulated Regrets for different bandit algorithms, averaged ${}$ times\nArms: ${}${}".format(self.repetitions, repr(self.envs[environmentId].arms), signature))
        else:
            plt.legend(loc='upper left', numpoints=1, fancybox=True, framealpha=0.7)  # http://matplotlib.org/users/recipes.html#transparent-fancy-legends
            plt.ylabel(r"Cumulated Regret $R_t = t \mu^* - \sum_{s = 1}^{t} \mathbb{E}_{%d}[r_s]$" % (self.repetitions,))
            plt.title("Cumulated Regrets for different bandit algorithms, averaged ${}$ times\nArms: ${}${}".format(self.repetitions, repr(self.envs[environmentId].arms), signature))
        maximizeWindow()
        if savefig is not None:
            print("Saving to", savefig, "...")
            plt.savefig(savefig, dpi=DPI, bbox_inches='tight')
        plt.show()

    def plotBestArmPulls(self, environmentId, savefig=None):
        plt.figure()
        colors = palette(self.nbPolicies)
        markers = makemarkers(self.nbPolicies)
        markers_on = np.arange(0, self.horizon, int(self.horizon / 10.0))
        delta_marker = 1 + int(self.horizon / 200.0)  # XXX put back 0 if needed
        for i, policy in enumerate(self.policies):
            Y = self.getBestArmPulls(i, environmentId)
            plt.plot(Y, label=str(policy), color=colors[i], marker=markers[i], markevery=(delta_marker * (i % self.envs[environmentId].nbArms) + markers_on))
        plt.legend(loc='upper left', numpoints=1, fancybox=True, framealpha=0.7)  # http://matplotlib.org/users/recipes.html#transparent-fancy-legends
        plt.xlabel(r"Time steps $t = 1 .. T$, horizon $T = {}$".format(self.horizon))
        plt.ylim(-0.03, 1.03)
        plt.ylabel(r"Frequency of pulls of the optimal arm")
        plt.title("Best arm pulls frequency for different bandit algorithms, averaged ${}$ times\nArms: ${}${}".format(self.repetitions, repr(self.envs[environmentId].arms), signature))
        maximizeWindow()
        if savefig is not None:
            print("Saving to", savefig, "...")
            plt.savefig(savefig, dpi=DPI, bbox_inches='tight')
        plt.show()

    def printFinalRanking(self, environmentId=0):
        assert 0 < self.averageOn < 1, "Error, the parameter averageOn of a EvaluatorMultiPlayers classs has to be in (0, 1) strictly, but is = {} here ...".format(self.averageOn)
        print("\nFinal ranking for this environment #{} :".format(environmentId))
        nbPolicies = self.nbPolicies
        lastY = np.zeros(nbPolicies)
        for i, policy in enumerate(self.policies):
            Y = self.getCumulatedRegret(i, environmentId)
            if self.finalRanksOnAverage:
                lastY[i] = np.mean(Y[-int(self.averageOn * self.horizon)])   # get average value during the last 0.5% of the iterations
            else:
                lastY[i] = Y[-1]  # get the last value
        # Sort lastY and give ranking
        index_of_sorting = np.argsort(lastY)
        for i, k in enumerate(index_of_sorting):
            policy = self.policies[k]
            print("- Policy '{}'\twas ranked\t{} / {} for this simulation (last regret = {:g}).".format(str(policy), i + 1, nbPolicies, lastY[k]))
        return lastY, index_of_sorting


# Helper function for the parallelization

# @profile  # DEBUG with kernprof (cf. https://github.com/rkern/line_profiler#kernprof
def delayed_play(env, policy, horizon,
                 random_shuffle=random_shuffle, random_invert=random_invert, nb_random_events=nb_random_events):
    # We have to deepcopy because this function is Parallel-ized
    env = deepcopy(env)
    policy = deepcopy(policy)
    horizon = deepcopy(horizon)
    # Start game
    policy.startGame()
    result = Result(env.nbArms, horizon)  # One Result object, for every policy
    # XXX Experimental support for random events: shuffling or inverting the list of arms, at these time steps
    t_events = [i * int(horizon / float(nb_random_events)) for i in range(nb_random_events)]
    if nb_random_events is None or nb_random_events <= 0:
        random_shuffle = False
        random_invert = False

    for t in range(horizon):
        choice = policy.choice()
        reward = env.arms[choice].draw(t)
        policy.getReward(choice, reward)
        result.store(t, choice, reward)
        # XXX Experimental : shuffle the arms at the middle of the simulation
        if random_shuffle:
            if t in t_events:  # XXX improve this: it is slow to test 'in <a list>', faster to compute a 't % ...'
                shuffle(env.arms)
                # print("Shuffling the arms ...")  # DEBUG
        # XXX Experimental : invert the order of the arms at the middle of the simulation
        if random_invert:
            if t in t_events:  # XXX improve this: it is slow to test 'in <a list>', faster to compute a 't % ...'
                env.arms = env.arms[::-1]
                # print("Inverting the order of the arms ...")  # DEBUG
    return result
