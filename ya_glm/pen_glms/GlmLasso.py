from ya_glm.base.Glm import Glm
from ya_glm.base.GlmCV import GlmCVSinglePen, GlmCVENet
from ya_glm.cv.CVPath import CVPathMixin
from ya_glm.cv.ENetCVPath import ENetCVPathMixin
from ya_glm.cv.CVGridSearch import CVGridSearchMixin

from ya_glm.pen_max.lasso import get_pen_max

from ya_glm.init_signature import add_from_classes
from ya_glm.utils import maybe_add, lasso_and_ridge_from_enet
from ya_glm.processing import check_estimator_type


class GlmLasso(Glm):

    @add_from_classes(Glm)
    def __init__(self, pen_val=1, lasso_weights=None,
                 ridge_pen_val=None, ridge_weights=None, tikhonov=None,
                 groups=None): pass

    def _get_solve_kws(self):
        """
        solve_glm is called as solve_glm(X=X, y=y, **kws)
        """

        if self.ridge_weights is not None and self.tikhonov is not None:
            raise ValueError("Both ridge weigths and tikhonov"
                             "cannot both be provided")

        loss_func, loss_kws = self.get_loss_info()

        kws = {'loss_func': loss_func,
               'loss_kws': loss_kws,

               'fit_intercept': self.fit_intercept,
               **self.opt_kws,

               'lasso_pen': self.pen_val,
               }

        ###################################
        # potential extra Lasso arguments #
        ###################################

        # let's only add these if they are not None
        # this way we can use solvers that doesn't have these kws
        extra_kws = {'lasso_weights': self.lasso_weights,
                     'ridge_pen': self.ridge_pen_val,
                     'ridge_weights': self.ridge_weights,
                     'tikhonov': self.tikhonov
                     }

        kws = maybe_add(kws, **extra_kws)

        ##################################
        # potential lasso type arguments #
        ##################################

        pen_kind = self._get_penalty_kind()
        if pen_kind == 'groups':
            kws['groups'] = self.groups

        elif pen_kind == 'multi_task':
            kws['L1to2'] = True

        elif pen_kind == 'nuc':
            kws['nuc'] = True

        return kws

    def _get_pen_val_max_from_pro(self, X, y, sample_weight=None):
        loss_func, loss_kws = self.get_loss_info()
        pen_kind = self._get_penalty_kind()

        kws = {'X': X,
               'y': y,
               'fit_intercept': self.fit_intercept,
               'loss_func': loss_func,
               'loss_kws': loss_kws,
               'weights': self.lasso_weights,
               'sample_weight': sample_weight
               }

        if pen_kind == 'group':
            kws['groups'] = self.groups

        return get_pen_max(pen_kind, **kws)


class GlmLassoCVPath(CVPathMixin, GlmCVSinglePen):

    def _get_solve_path_kws(self):
        if not hasattr(self, 'pen_val_seq_'):
            raise RuntimeError("pen_val_seq_ has not yet been set")

        kws = self.estimator._get_solve_kws()
        del kws['lasso_pen']
        kws['lasso_pen_seq'] = self.pen_val_seq_
        return kws

    def _check_base_estimator(self, estimator):
        check_estimator_type(estimator, GlmLasso)


class GlmLassoCVGridSearch(CVGridSearchMixin, GlmCVSinglePen):
    def _check_base_estimator(self, estimator):
        check_estimator_type(estimator, GlmLasso)


class GlmENet(Glm):

    @add_from_classes(Glm)
    def __init__(self, pen_val=1, l1_ratio=0.5,
                 lasso_weights=None, ridge_weights=None, tikhonov=None,
                 groups=None): pass

    def _get_solve_kws(self):
        """
        solve_glm is called as solve_glm(X=X, y=y, **kws)
        """

        if self.ridge_weights is not None and self.tikhonov is not None:
            raise ValueError("Both ridge weigths and tikhonov"
                             "cannot both be provided")

        loss_func, loss_kws = self.get_loss_info()

        lasso_pen, ridge_pen = \
            lasso_and_ridge_from_enet(pen_val=self.pen_val,
                                      l1_ratio=self.l1_ratio)

        kws = {'loss_func': loss_func,
               'loss_kws': loss_kws,

               'fit_intercept': self.fit_intercept,
               **self.opt_kws,

               'lasso_pen': lasso_pen,
               'ridge_pen': ridge_pen
               }

        ###################################
        # potential extra Lasso arguments #
        ###################################

        # let's only add these if they are not None
        # this way we can use solvers that doesn't have these kws
        extra_kws = {'lasso_weights': self.lasso_weights,
                     'ridge_weights': self.ridge_weights,
                     'tikhonov': self.tikhonov
                     }

        kws = maybe_add(kws, **extra_kws)

        ##################################
        # potential lasso type arguments #
        ##################################

        pen_kind = self._get_penalty_kind()
        if pen_kind == 'groups':
            kws['groups'] = self.groups

        elif pen_kind == 'multi_task':
            kws['L1to2'] = True

        elif pen_kind == 'nuc':
            kws['nuc'] = True

        return kws

    def _get_pen_val_max_from_pro(self, X, y, sample_weight=None):
        loss_func, loss_kws = self.get_loss_info()
        pen_kind = self._get_penalty_kind()

        kws = {'X': X,
               'y': y,
               'fit_intercept': self.fit_intercept,
               'loss_func': loss_func,
               'loss_kws': loss_kws,
               'weights': self.lasso_weights,
               'sample_weight': sample_weight
               }

        if pen_kind == 'group':
            kws['groups'] = self.groups

        l1_max = get_pen_max(pen_kind, **kws)

        return l1_max / self.l1_ratio


class GlmENetCVPath(ENetCVPathMixin, GlmCVENet):
    solve_glm_path = None

    def _get_solve_path_enet_base_kws(self):
        kws = self.estimator._get_solve_kws()
        del kws['lasso_pen']
        del kws['ridge_pen']
        return kws

    def _check_base_estimator(self, estimator):
        check_estimator_type(estimator, GlmENet)


class GlmENetCVGridSearch(CVGridSearchMixin, GlmCVSinglePen):
    def _check_base_estimator(self, estimator):
        check_estimator_type(estimator, GlmENet)
