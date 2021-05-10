import math
import numpy as np
import database
from svd import factorization
from utils import multiply_sparse
from scipy.spatial import distance
from database import load_docs, load_vocabulary2
from config import Configuration
from tqdm import tqdm


class Vocabulary:
    def __init__(self):
        self.items = database.vocabulary_vector()
        self.itemsSet = set(self.items)
        self.__indexes__ = {}
        for i, w in enumerate(self.items):
            self.__indexes__[w] = i

    def __getitem__(self, word):
        return self.__indexes__[word]

    def vectorize_query(self, query, weights=None):
        v = [0 for _ in range(len(self.items))]
        tf={}
        N = database.documents_len()
        for word in query:
            try:
                tf[word]+=1
            except KeyError:
                tf[word]=1
        for word in query:
            index=self.__indexes__[word]
            v[index]= tf[word] * math.log2((N+1) / (0.5 + database.DF(index)))
        return v


class DataSet:
    def __init__(self, documents_file):
        if not Configuration['alreadyInit']:
            load_docs(documents_file)
            load_vocabulary2()
            database.calculate_tf()
            database.calculate_df()
        self.W = [[0 for _ in range(database.documents_len())] for _ in range(database.vocabulary_len())]
        self.__build_w__()

    def __build_w__(self):
        if Configuration['alreadyInit']:
            print("Load W from W.npy file")
            self.W = np.load('W.npy')
        else:
            print("Building W matrix")
            N = database.documents_len()
            for i in tqdm(range(database.vocabulary_len()), unit=' word'):
                df = database.DF(i)
                for j in range(N):
                    self.W[i, j] = database.TF(i, j) * math.log2(N / (1 + df))
            print("Save W matrix to W.npy file")
            np.save('W', self.W)

    def find_relevance(self, query, k=None):
        # Query q has m dimensions (vocabulary size)
        terms, diag, docs = factorization(self.W, 200)

        diag=[1/x for x in diag]
        query_repres=np.dot(np.transpose(terms), query)

        query_repres = multiply_sparse(diag, query_repres)
        docs=np.transpose(docs)
        
        recovered={i: distance.cosine(query_repres, elem) for i, elem in enumerate(docs)}
        for elem in sorted(recovered, key=recovered.get):
            yield elem


class MRI:
    def __init__(self, vocabulary_file, documents_file):
        # Load dataset
        self.dataSet = DataSet(documents_file)
        # Load vocabulary
        self.vocabulary = Vocabulary()

    def __call__(self, query, k=None):
        return self.dataSet.find_relevance(self.vocabulary.vectorize_query(query), k)


mri = MRI(vocabulary_file='vocabulary.txt', documents_file='CISI.ALL.json')
