from ya_glm.solver.base import GlmSolverWithPath
from ya_glm.autoassign import autoassign
from ya_glm.opt.fista import solve_fista

from ya_glm.opt.glm_loss.from_config import get_glm_loss_func
from ya_glm.opt.penalty.from_config import get_penalty_func, wrap_intercept
from ya_glm.opt.constraint.from_config import get_constraint_func

from ya_glm.opt.base import Sum
from ya_glm.opt.utils import decat_coef_inter_vec, decat_coef_inter_mat

from ya_glm.utils import is_multi_response


class FISTA(GlmSolverWithPath):
    """
    Solves a penalized GLM problem using the FISTA algorithm.

    Parameters
    ----------
    max_iter: int
        Maximum number of iterations.

    xtol: float, None
        Stopping criterion based on max norm of successive iteration differences i.e. stop if max(x_new - x_prev) < xtol.

    rtol: float, None
        Stopping criterion based on the relative difference of successive loss function values i.e. stop if abs(loss_new - loss_prev)/loss_new < rtol.

    atol: float, None
        Stopping criterion based on the absolute difference of successive loss function values i.e. stop if abs(loss_new - loss_prev) < atol.

    bt_max_steps: int
        Maximum number of backtracking steps to take.

    bt_shrink: float
        How much to shrink the step size in each backtracking step. Should lie strictly in the unit interval.

    bt_grow: float, None
        (Optional) How much to grow the step size each iteraction when using backgracking.

    accel: bool
        Whether or not to use FISTA acceleration.

    restart: bool
        Whether or not to restart the acceleration scheme. See (13) from https://bodono.github.io/publications/adap_restart.pdf
        for the strategy we employ.

    tracking_level: int
        How much data to track.
    """

    @autoassign
    def __init__(self,
                 max_iter=1000,
                 xtol=1e-4,
                 rtol=None,
                 atol=None,
                 bt_max_steps=20,
                 bt_shrink=0.5,
                 bt_grow=1.1,
                 accel=True,
                 restart=True,
                 tracking_level=0): pass

    def setup(self, X, y, loss, penalty, constraint=None,
              fit_intercept=True, sample_weight=None):
        """
        Sets up anything the solver needs.
        """
        self.is_mr_ = is_multi_response(y)
        self.fit_intercept_ = fit_intercept
        self.penalty_config_ = penalty

        #################
        # Loss function #
        #################

        # get the loss function
        self.loss_func_ = get_glm_loss_func(config=loss, X=X, y=y,
                                            fit_intercept=fit_intercept,
                                            sample_weight=sample_weight)

        # compute lipchtiz etc
        self.loss_func_.setup()

        if not self.loss_func_.is_smooth:
            raise NotImplementedError("The loss function must be smooth for"
                                      " FISTA, but {} is not".
                                      format(loss.name))

        ##########################
        # Penalty and constraint #
        ##########################

        self.penalty_func_ = None
        self.constraint_func_ = None

        # get the penalty
        if penalty is not None and constraint is not None:
            raise NotImplementedError("FISTA can only handle either a "
                                      "constraint or a penalty, not both.")

        elif penalty is not None:
            self.penalty_func_ = get_penalty_func(config=self.penalty_config_)

        elif constraint is not None:
            self.constraint_func_ = get_constraint_func(config=constraint)

    def update_penalty(self, **params):
        """
        Updates the penalty parameters.
        """

        self.penalty_config_.set_params(**params)
        self.penalty_func_ = get_penalty_func(config=self.penalty_config_)

    def solve(self, coef_init=None, intercept_init=None, other_init=None):
        """
        Solves the optimization problem.

        Parameters
        ----------
        coef_init: None, array-like
            (Optional) Initialization for the coefficient.

        intercept_init: None, array-like
            (Optional) Initialization for the intercept.

        other_init: None, array-like
            (Optional) Initialization for other optimization data e.g. dual variables.

        Output
        ------
        soln, other_data, opt_info

        soln: dict of array-like
            The coefficient/intercept solutions,

        other_data: dict
            Other optimzation output data e.g. dual variables.

        opt_info: dict
            Optimization information e.g. number of iterations, runtime, etc.
        """

        #########
        # Setup #
        #########

        # maybe add an intercept to the penalty
        if self.penalty_func_ is not None:
            penalty_func = wrap_intercept(func=self.penalty_func_,
                                          fit_intercept=self.fit_intercept_,
                                          is_mr=self.is_mr_)
        else:
            penalty_func = None

        # set smooth/non-smooth functions
        if penalty_func is None:
            smooth_func = self.loss_func_
            non_smooth_func = self.constraint_func_

        elif penalty_func.is_smooth:
            smooth_func = Sum([self.loss_func_, penalty_func])
            non_smooth_func = None
        else:
            smooth_func = self.loss_func_
            non_smooth_func = penalty_func

        # setup step size/backtracking
        if smooth_func.grad_lip is not None:
            # use Lipchtiz constant if it is available
            step = 'lip'
            backtracking = False
        else:
            step = 1  # TODO: perhaps smarter base step size?
            backtracking = True

        # setup initial value
        if coef_init is None or  \
                (self.fit_intercept_ and intercept_init is None):
            init_val = self.loss_func_.default_init()
        else:
            init_val = self.loss_func_.\
                cat_intercept_coef(intercept_init, coef_init)

        ############################
        # solve problem with FISTA #
        ############################
        soln, out = solve_fista(smooth_func=smooth_func,
                                init_val=init_val,
                                non_smooth_func=non_smooth_func,
                                step=step,
                                backtracking=backtracking,
                                **self.get_solve_kws())

        # format output
        if self.fit_intercept_:
            if self.is_mr_:
                coef, intercept = decat_coef_inter_mat(soln)
            else:
                coef, intercept = decat_coef_inter_vec(soln)
        else:
            coef = soln
            intercept = None

        soln = {'coef': coef, 'intercept': intercept}
        opt_data = None
        opt_info = out

        return soln, opt_data, opt_info
