python -m grecy install grc_proiel_trf

#After installing grc_proiel_trf or any other model
import spacy

nlp = spacy.load('grc_proiel_trf')
doc = nlp('δοκῶ μοι περὶ ὧν πυνθάνεσθε οὐκ ἀμελέτητος εἶναι')

for token in doc:
   print(f'{token.text}, lemma: {token.lemma_}, pos: {token.pos_}, dep: {token.dep_}')
