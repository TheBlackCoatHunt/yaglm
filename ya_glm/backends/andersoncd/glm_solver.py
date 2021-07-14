import numpy as np
from scipy import sparse
from numpy.linalg import norm
from sklearn.utils import check_array

from andersoncd.penalties import L1, WeightedL1, L1_plus_L2
from andersoncd.solver import solver

from ya_glm.backends.fista.glm_solver import process_param_path


def solve_glm(X, y,
              loss_func='lin_reg',
              loss_kws={},
              fit_intercept=True,

              lasso_pen=None,
              lasso_weights=None,

              # groups=None,
              # L1to2=False,
              # nuc=False,
              # ridge_pen=None,
              # ridge_weights=None,
              # tikhonov=None,

              coef_init=None,
              intercept_init=None,

              max_iter=20, max_epochs=50000,
              p0=10, verbose=0, tol=1e-4, prune=0,
              return_n_iter=False):

    X = check_array(X, 'csc', dtype=[np.float64, np.float32],
                    order='F', copy=False, accept_large_sparse=False)
    y = check_array(y, 'csc', dtype=X.dtype.type, order='F', copy=False,
                    ensure_2d=False)

    # check_args(X=X, y=y, loss_func=loss_func,
    #            loss_kws=loss_kws,
    #            fit_intercept=fit_intercept,
    #            lasso_pen=lasso_pen,
    #            lasso_weights=lasso_weights,
    #            groups=groups,
    #            L1to2=L1to2,
    #            nuc=nuc,
    #            ridge_pen=ridge_pen,
    #            ridge_weights=ridge_weights,
    #            tikhonov=tikhonov)

    #######################################
    # setup initialization and other data #
    #######################################
    
    penalty = get_penalty(lasso_pen=lasso_pen,
                          lasso_weights=lasso_weights,
                          ridge_pen=ridge_pen)
    
    if coef_init is None:
        coef_init = np.zeros(X.shape[1], dtype=X.dtype)
        R = y.copy()
    else:
        p0 = max((coef_init != 0.).sum(), p0)
        R = y - X @ coef_init

    norms_X_col = norm(X, axis=0)
    
    coef, obj_hist, kkt_max = solver(X=X, y=y,
                                     penalty=penalty,
                                     w=coef_init.copy(),
                                     R=R, norms_X_col=norms_X_col,
                                     max_iter=max_iter,
                                     max_epochs=max_epochs,
                                     p0=p0,
                                     tol=tol,
                                     verbose=verbose)

    opt_out = {'objective': obj_hist,
               'kkt_max': kkt_max}
    
    intercept = None
    
    return coef, intercept, opt_out


def solve_glm_path(X, y,
                   lasso_pen_seq=None, ridge_pen_seq=None,
                   
                   check_decr=True, generator=True,

                   loss_func='lin_reg',
                   loss_kws={},
                   fit_intercept=True,

                   lasso_pen=None,
                   lasso_weights=None,
                   # groups=None,
                   # L1to2=False,
                   # nuc=False,
                   # ridge_pen=None,
                   # ridge_weights=None,
                   # tikhonov=None,

                   coef_init=None,
                   intercept_init=None,

                   max_iter=20, max_epochs=50000,
                   p0=10, verbose=0, tol=1e-4, prune=0,
                   return_n_iter=False):

    X = check_array(X, 'csc', dtype=[np.float64, np.float32],
                    order='F', copy=False, accept_large_sparse=False)
    y = check_array(y, 'csc', dtype=X.dtype.type, order='F', copy=False,
                    ensure_2d=False)

    param_path = process_param_path(lasso_pen_seq=lasso_pen_seq,
                                    ridge_pen_seq=ridge_pen_seq,
                                    check_decr=check_decr)
    
    # if 'lasso_pen' in param_path:
    #     temp_lasso_pen = param_path['lasso_pen'][0]
    # else:
    #     temp_lasso_pen = lasso_pen
       
    # if 'ridge_pen' in param_path:
    #     temp_ridge_pen = param_path['ridge_pen'][0]
    # else:
    #     temp_ridge_pen = ridge_pen

    # check_args(X=X, y=y, loss_func=loss_func,
    #            loss_kws=loss_kws,
    #            fit_intercept=fit_intercept,
    #            lasso_pen=temp_lasso_pen,
    #            lasso_weights=lasso_weights,
    #            groups=groups,
    #            L1to2=L1to2,
    #            nuc=nuc,
    #            ridge_pen=temp_ridge_pen,
    #            ridge_weights=ridge_weights,
    #            tikhonov=tikhonov)

    #######################################
    # setup initialization and other data #
    #######################################
    
    if coef_init is None:
        coef = np.zeros(X.shape[1], dtype=X.dtype)
        R = y.copy()
    else:
        coef = coef_init.copy()
        R = y - X @ coef_init

    norms_X_col = norm(X, axis=0)

    solve_verbose = verbose >= 2
    n_params = len(param_path)
    for i, params in enumerate(param_path):
        if verbose >= 1:
            print('Solving path parameter {}/{}'.format(i, n_params))
        
        # set penalty for this path
        penalty = get_penalty(lasso_weights=lasso_weights,
                              **params)

        # solve!
        p0 = max((coef != 0.).sum(), p0)

        coef, obj_hist, kkt_max = solver(X=X, y=y,
                                         penalty=penalty,
                                         w=coef,
                                         R=R,
                                         norms_X_col=norms_X_col,
                                         max_iter=max_iter,
                                         max_epochs=max_epochs,
                                         p0=p0,
                                         tol=tol,
                                         verbose=solve_verbose)

        # format output
        fit_out = {'coef': coef,
                   'intercept': None,
                   'opt_data':  {'objective': obj_hist,
                                 'kkt_max': kkt_max}}

    #     if generator:
        yield fit_out, params
    #     else:
    #         out.append((fit_out, params))

    # return out


# def check_args(X, y,
#                loss_func,
#                loss_kws,
#                fit_intercept,

#                lasso_pen,
#                lasso_weights,
#                groups,
#                L1to2,
#                nuc,
#                ridge_pen,
#                ridge_weights,
#                tikhonov):

#     #############################
#     # check what is implemented #
#     #############################

#     if loss_func != 'lin_reg':
#         raise NotImplementedError("{} is not supported".format(loss_func))

#     if fit_intercept:
#         raise NotImplementedError("intercept not supported")

#     if groups is not None:
#         raise NotImplementedError("groups is not supported")

#     if L1to2:
#         raise NotImplementedError("L1to2 is not yet supported")

#     if nuc:
#         raise NotImplementedError("nuc is not yet supported")

#     if tikhonov is not None:
#         raise NotImplementedError("tikhonov is not yet supported")

#     if ridge_weights is not None:
#         raise NotImplementedError("ridge_weights is not yet supported")

#     if ridge_pen is not None and lasso_weights is not None:
#         raise NotImplementedError("lasso_weights and ridge penalty not yet supported")

#     if sparse.issparse(X):
#         raise ValueError("Spare design matrices are not supported yet.")


def get_penalty(lasso_pen=None, lasso_weights=None, ridge_pen=None):
    #############################
    # pre process penalty input #
    #############################

    if lasso_pen is None and lasso_weights is not None:
        lasso_pen = 1
    elif lasso_pen is None:
        lasso_pen = 0

    #################
    # Setup penalty #
    #################

    if lasso_weights is None:
        if ridge_pen is None:
            penalty = L1(alpha=lasso_pen)
        else:
            alpha = lasso_pen + ridge_pen
            l1_ratio = lasso_pen / alpha
            penalty = L1_plus_L2(alpha=alpha, l1_ratio=l1_ratio)

    else:
        if ridge_pen is not None:
            raise NotImplementedError

        penalty = WeightedL1(alpha=lasso_pen,
                             weights=np.array(lasso_weights).astype(float))

    return penalty
