import timeit
from timeit import default_timer as timer
from pympler import asizeof
import sys
import score_data
import loc_data
import scoring_methods


def resources_test(run_all_implementations=True):
    # Let's read in portions of a big matrix in increasing size, and for each size, score all pairs (both sparse and dense).
    # This will let us see how things scale and where memory limits will come in.
    infile = "/Users/lfriedl/Documents/dissertation/real-data/brightkite/bipartite_adj.txt"

    num_nodes = (100, 1000, 10000, 100000)
    num_nodes = [10000]  # this size: no run finished in the length of time I was willing to wait
    num_nodes = [500]
    for num_to_try in num_nodes:
        adj_mat, _ = loc_data.read_loc_adj_mat(infile, max_rows=num_to_try)

        pi_vector_learned = score_data.learn_pi_vector(adj_mat)
        pi_vector_preproc, adj_mat_preproc = score_data.adjust_pi_vector(pi_vector_learned, adj_mat)

        # (order given here doesn't matter)
        methods_to_run = ['cosine', 'cosineIDF',
                          # use fast "transform"
                          'shared_size', 'adamic_adar', 'newman', 'shared_weight11',
                          # medium
                          'hamming', 'pearson', 'jaccard',
                          # WC uses "transform" when dense, "terms" when sparse -- speed varies accordingly
                          'weighted_corr',
                          # only have slow "terms" method
                          'shared_weight1100', 'mixed_pairs']

        adj_mat_preproc_dense = adj_mat_preproc.toarray()
        print "\ndense version takes up " + str(sys.getsizeof(adj_mat_preproc_dense)) + " bytes"

        start = timer()
        score_data.scoring_methods.score_pairs(score_data.gen_all_pairs, adj_mat_preproc_dense,
                                               which_methods=methods_to_run,
                                               pi_vector=pi_vector_preproc, back_compat=True,
                                               num_docs=adj_mat_preproc.shape[0],
                                               mixed_pairs_sims=[.01],
                                               print_timing=True,
                                               run_all_implementations=run_all_implementations)
        end = timer()
        print "for matrix with " + str(adj_mat_preproc.shape[0]) + " items, " + str(adj_mat_preproc.shape[1]) \
              + " affils, "
        print "ran all methods using dense matrix in " + str(end - start) + " seconds"

        print "\nsparse adj_matrix takes up " + str(asizeof.asizeof(adj_mat_preproc)) + " bytes;"

        start = timer()
        score_data.scoring_methods.score_pairs(score_data.gen_all_pairs, adj_mat_preproc,
                                               which_methods=methods_to_run,
                                               pi_vector=pi_vector_preproc, back_compat=True,
                                               num_docs=adj_mat_preproc.shape[0],
                                               mixed_pairs_sims=[.01],
                                               print_timing=True,
                                               run_all_implementations=run_all_implementations)
        end = timer()
        print "for matrix with " + str(adj_mat_preproc.shape[0]) + " items, " + str(adj_mat_preproc.shape[1]) \
              + " affils, "
        print "ran all methods using sparse matrix in " + str(end - start) + " seconds"


# To nail down which versions of a few methods are fastest
def test_timings(infile, num_reps=100):
    print "Testing timings using infile " + infile + ", each method run " + str(num_reps) + " times"
    # notice: strings prepped for timeit() need to have no indentation
    # note 2: timeit() module (further) recommends calling .repeat(), which does the whole call 3 times, and keep the min value.
    setup = """
import extra_implementations
import score_data
import scoring_methods
import scoring_methods_fast
import transforms_for_dot_prods
""" + \
            "adj_mat_infile = '" + infile + "'" + """
adj_mat = score_data.load_adj_mat(adj_mat_infile)
pi_vector_learned = score_data.learn_pi_vector(adj_mat)
pi_vector_preproc, adj_mat_preproc = score_data.adjust_pi_vector(pi_vector_learned, adj_mat)
"""

    s = """extra_implementations.simple_only_weighted_corr(score_data.gen_all_pairs, adj_mat_preproc,
                                                                    pi_vector_preproc, print_timing=False)
    """
    print "** weighted_corr **"
    print "simple_only_weighted_corr: " + str(timeit.timeit(s, setup=setup, number=num_reps))

    s2 = """scoring_methods.compute_scores_with_transform(score_data.gen_all_pairs, adj_mat_preproc, 
                                transforms_for_dot_prods.wc_transform, pi_vector=pi_vector_preproc, print_timing=False)
    """
    print "wc_transform: " + str(timeit.timeit(s2, setup=setup, number=num_reps))
    # --> wc_transform is faster for weighted_corr (both made matrix dense)

    s3 = """scoring_methods.compute_scores_from_terms(score_data.gen_all_pairs, adj_mat_preproc, scoring_methods.wc_terms,
                        pi_vector=pi_vector_preproc,
                        num_affils=adj_mat_preproc.shape[1], print_timing=False)
    """
    print "wc_terms: " + str(timeit.timeit(s3, setup=setup, number=num_reps))

    s4 = """extra_implementations.simple_weighted_corr_sparse(score_data.gen_all_pairs, adj_mat_preproc, 
                                                pi_vector=pi_vector_preproc, print_timing=False)    
    """
    print "simple_weighted_corr_sparse: " + str(timeit.timeit(s4, setup=setup, number=num_reps))
    # --> for sparse matrix, wc_terms is faster than simple_weighted_corr_sparse

    print "** Adamic-adar **"
    s5 = """scoring_methods.compute_scores_with_transform(score_data.gen_all_pairs, adj_mat_preproc,
                                              transforms_for_dot_prods.adamic_adar_transform, 
                                              num_docs=adj_mat_preproc.shape[0], pi_vector=pi_vector_preproc)
    """
    print "adamic_adar_transform: " + str(timeit.timeit(s5, setup=setup, number=num_reps))

    s6 = """
num_docs_word_occurs_in = np.maximum(adj_mat_preproc.shape[0] * pi_vector_preproc, 2)
extra_implementations.simple_only_adamic_adar_scores(score_data.gen_all_pairs, adj_mat_preproc,
                                                     num_docs_word_occurs_in)
"""
    print "simple_only_adamic_adar_scores: " + str(timeit.timeit(s5, setup=setup, number=num_reps))
    # --> simple_only_adamic_adar_scores sometimes faster, sometimes slower

    print "** Pearson **"
    s6 = "extra_implementations.simple_only_phi_coeff(score_data.gen_all_pairs, adj_mat_preproc)"
    print "simple_only_phi_coeff: " + str(timeit.timeit(s6, setup=setup, number=num_reps))

    s7 = "scoring_methods_fast.simple_only_pearson(score_data.gen_all_pairs, adj_mat_preproc)"
    print "simple_only_pearson: " + str(timeit.timeit(s7, setup=setup, number=num_reps))
    # simple_only_pearson was a bit faster


if __name__ == "__main__":
    # resources_test(run_all_implementations=False)
    test_timings("../tests/ng_aa_data2/data2_adjMat_quarterAffils.mtx.gz")
    test_timings("../tests/reality_appweek_50/data50_adjMat.mtx.gz")