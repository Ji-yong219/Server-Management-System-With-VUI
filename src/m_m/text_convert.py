from konlpy.tag import Hannanum
import re
from difflib import get_close_matches

han = Hannanum()

list_changed = []

def get_NJP(text):
    type_ = 'None'
    with open("./src/m_m/ttc.csv", "r") as f:
        p = f.read()
        
    check_P = [(i.split(";")[0], i.split(";")[1]) for i in p.split("\n")]
    
    data = han.pos(text)
    list_N = []
    list_P = []
    action2 = 'None'
    for pos_tag in data:
        if pos_tag[1] == 'N':
            list_N.append(pos_tag[0])
        elif pos_tag[1] == 'P' and pos_tag[0] != '리' and pos_tag[0] != '이':
            for i in check_P:
                if i[0] == pos_tag[0]:
                    type_ = i[1]

    list_N = matching(list_N)
    return list_N, type_, action2

def distortion(sentence):
    with open("./src/m_m/distortion.csv", "r") as f:
        word = f.read()
    
    distort = [(i.split(";")[0], i.split(";")[1]) for i in word.split("\n")]

    for i in distort:
        sentence = sentence.replace(i[0], i[1])

    print("전처리 후 문장:", sentence)
    return sentence
    
def verb_change(sentence):
    with open("./src/m_m/dic.csv", "r") as f:
        verb = f.read()

    ch_verb = [(i.split(";")[0], i.split(";")[1]) for i in verb.split("\n")]

    for i in ch_verb:
        if i[0] in sentence:
            list_changed.append([i[0], i[1]])
            sentence = sentence.replace(i[0], i[1])
    return sentence

def window(sentence):
    sentence = sentence.replace("패이지", " 페이지")
    
    p = '[1-9일이삼사오육칠팔구십]{1,2}[번] *창*에*서*'
    win = re.findall(p, sentence)

    if len(win) != 0:
        sentence = ''.join(sentence).split(''.join(win))[1]
        win = ''.join(''.join(win).split('번')[0])
        if not win.isdigit():
            win = win.translate(str.maketrans('일이삼사오육칠팔구', '123456789'))
    else:
        win = 'last'
        
    return win, sentence

def matching(n_list):
    with open("./src/m_m/similar.csv", "r") as f:
        similar = f.read()
    
    similar_list = similar.split('\n')
    # print(similar_list)
    # print(n_list)
    for i in range(len(n_list)):
        if len(get_close_matches(n_list[i], similar_list)) != 0:
            n_list[i] = get_close_matches(n_list[i], similar_list)[0]
            
    return n_list
    
    
def extract_target(sentence,server_list): 
    index_w = [] 
    min = 0
    target = 'None'
    
    for i in server_list:
        if i[0].replace(' ', '') in sentence.replace(' ', ''):
            for j in range(len(sentence)):
                if i[0][0] == sentence[j]:
                    index_w.append(j)
            target = i[1]
            break            

        elif i[0].replace(' ', '').translate(
                    str.maketrans('123456789','일이삼사오육칠팔구')
                ) in sentence.replace(' ', ''):
            
            for j in range(len(sentence)):
                if i[0][0] == sentence[j]:
                    index_w.append(j)
            target = i[1]
            break

    if target == 'None':
        return sentence, target
    if len(index_w) > 0:
        for i in index_w:
            if min == 0 or sentence.index('서버')-i < min :
                min = i
    sentence = sentence[:min] + sentence[sentence.index("서버")+2:]
    
    return sentence, target

def restore_sentence(sentence):
    for i in list_changed:
        if i[1] in sentence:
            sentence = sentence.replace(i[1], i[0])
    return sentence

def convert_command(sentence, server_list):
    win = 'None'
    action1 = 'None'
    server_info = []
    
    for i in range(len(server_list)):
        server_info.append([
            server_list[i].split(':')[0],
            server_list[i].split(':')[1]
        ])
        
    sentence = distortion(sentence)
    sentence = verb_change(sentence)
    win, sentence = window(sentence)
    sentence, target = extract_target(sentence, server_info)
    sentence = sentence.replace('  ', ' ')
    sentence, type_, action2 = get_NJP(sentence)
    action1 = restore_sentence(' '.join(sentence))

    if len(action1) > 0:
        return {'window':win, 'type':type_,'target':target, 'action':action1}

    else:
        if win != 'last' and action2 == 'None':
            action2 = '창'
        return {'window':win, 'type':type_,'target':target, 'action':action2}