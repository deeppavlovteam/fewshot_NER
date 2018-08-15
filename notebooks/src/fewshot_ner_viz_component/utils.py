import numpy as np
import copy

# Utility functions
def get_tokens_len(tokens):
    if isinstance(tokens[0], str):
        tokens = [tokens]
    return [len(seq) for seq in tokens]

def to_lower_case(tokens:list):
    tokens_lower = []
    for seq in tokens:
        tokens_lower.append([])
        for token in seq:
            tokens_lower[-1].append(token.lower())
    return tokens_lower

def add_padding(tokens:list):
    if isinstance(tokens[0], str):
        return tokens, len(tokens)
    elif isinstance(tokens[0], list):
        tokens = copy.deepcopy(tokens)
        max_len = 0
        for seq in tokens:
            if len(seq) > max_len:
                max_len = len(seq)
        for seq in tokens:
            i = len(seq)
            while i < max_len:
                seq.append('')
                i += 1
        return tokens
    else:
        raise Exception('tokens should be either list of strings or list of lists of strings')

def calc_sim(token_vec, support_vec)->dict:
    sim = {}
    sim['euc_dist'] = np.exp(-np.linalg.norm(token_vec - support_vec))
    sim['dot_prod'] = np.dot(token_vec, support_vec)
    sim['cosine'] = np.dot(token_vec, support_vec)/(np.linalg.norm(token_vec)*np.linalg.norm(support_vec)) if np.linalg.norm(support_vec) != 0 else 0
    return sim

def calc_sim_batch(tokens: list, embeddings: np.ndarray, support_vec: np.ndarray)->list:
    sim_list = []
    tokens_length = get_tokens_len(tokens)
    for i in range(len(tokens_length)):
        sim_list.append([])
        for j in range(tokens_length[i]):
            token_vec = embeddings[i,j,:]
            sim_list[i].append(calc_sim(token_vec, support_vec))
    return sim_list

def get_tokens_count(tokens:list):
    return len([t for seq in tokens for t in seq])
def embeddings2feat_mat(embeddings:np.ndarray, tokens_length):
    n_tokens = sum(tokens_length)
    n_features = embeddings.shape[-1]
    feat_mat = np.zeros((n_tokens, n_features))
#     print(feat_mat.shape)
    k = 0
    for i in range(len(tokens_length)):
        for j in range(tokens_length[i]):
            feat_mat[k, :] = embeddings[i, j, :]
            k += 1
    return feat_mat

def flatten_list(ar:list):
    flat = []
    for sublist in ar:
        flat += sublist
    return flat

def getNeTagMainPart(tag:str):
    return tag[2:] if tag != 'O' else tag

def tags2binaryFlat(tags):
    return np.array([1 if t == 'T' else 0 for seq in tags for t in seq])

def flatten_sim(sim_list):
    sims_flat = {'euc_dist': [], 'dot_prod': [], 'cosine': []}
    for i in range(len(sim_list)):
        for j in range(len(sim_list[i])):
            for sim_type in ['euc_dist', 'dot_prod', 'cosine']:
                sim = sim_list[i][j].get(sim_type)
                if sim != None:
                    sims_flat[sim_type].append(sim)
    for sim_type in ['euc_dist', 'dot_prod', 'cosine']:
        sims_flat[sim_type] = np.array(sims_flat[sim_type])
    return sims_flat

def calc_sim_min_max(sim_list, single_metric=False):
    if single_metric:
        sim_flat = flatten_list(sim_list)
    else:
        sim_flat = flatten_sim(sim_list)['cosine']
    sim_min = np.min(sim_flat)
    sim_max = np.max(sim_flat)
    return (sim_min, sim_max)

def sim_transform(sim, sim_min, sim_max, T=0.5):
    # similarity transformation with temperature for better visualization
    return (np.exp(sim/T) - np.exp(sim_min/T))/(np.exp(sim_max/T) - np.exp(sim_min/T))

def infer_tags(sim_list, sim_type, T=0.5, threshold=0.5):
    sim_min, sim_max = calc_sim_min_max(sim_list)
    tokens_length = get_tokens_len(sim_list)
    tags = [['T' if sim_transform(sim_list[i][j][sim_type], sim_min, sim_max, T)  > threshold else 'O' for j in range(tokens_length[i])] for i in range(len(tokens_length))]
    return tags

def split_tokens_tags(dataset: list):
    tokens = []
    tags = []
    for sample in dataset:
        tokens.append(sample[0])
        tags.append(sample[1])
    return tokens, tags

def calc_data_props(tokens:list, tags:list):
    props = {}
    props['ne_types'] = {}
    tokens_flat = flatten_list(tokens)
    tags_flat = flatten_list(tags)
    ne_count = 0
    for tag in tags_flat:
        if tag != 'O':
            ne_count += 1
            tag_main = tag[2:]
            if props['ne_types'].get(tag_main) != None:
                props['ne_types'][tag_main] += 1
            else:
                props['ne_types'][tag_main] = 1
    props['sent_count'] = len(tokens)
    props['tokens_count'] = len(tokens_flat)
    props['ne_count'] = ne_count
    props['ne_ratio'] = props['ne_count']/props['tokens_count']
    for k in props['ne_types'].keys():
        props['ne_types'][k] /= ne_count

    return props

def print_data_props(props:dict):
    s = ''
    s += '#sentences = {}, '.format(props['sent_count'])
    s += '#tokens = {}, '.format(props['tokens_count'])
    s += '#ne = {}, '.format(props['ne_count'])
    s += '#ne / #tokens = {:.3f}, '.format(props['ne_ratio'])
    print(s)

def softmax(ar, scale=True):
    ar = ar[:]
    eps = 1e-10
    if scale:
        ar_min = np.min(ar)
        ar_max = np.max(ar)
        if abs(ar_max - ar_min) > eps:
            ar = (ar - ar_min)/(ar_max - ar_min)
    return np.exp(ar)/(np.sum(np.exp(ar)))