from ijcai15 import PersTour

algo = PersTour('./Osaka', 'userVisits-Osak.csv')
algo.recommend(0.0)
algo.recommend(0.5)
algo.recommend(0.5, time_based=False)
algo.recommend(1.0)
algo.recommend(1.0, time_based=False)

algo = PersTour('./Edinburgh', 'userVisits-Edin.csv')
algo.recommend(0.0)
algo.recommend(0.5)
algo.recommend(0.5, time_based=False)
algo.recommend(1.0)
algo.recommend(1.0, time_based=False)

algo = PersTour('./Glasgow', 'userVisits-Glas.csv')
algo.recommend(0.0)
algo.recommend(0.5)
algo.recommend(0.5, time_based=False)
algo.recommend(1.0)
algo.recommend(1.0, time_based=False)

algo = PersTour('./Toronto', 'userVisits-Toro.csv')
algo.recommend(0.0)
algo.recommend(0.5)
algo.recommend(0.5, time_based=False)
algo.recommend(1.0)
algo.recommend(1.0, time_based=False)
