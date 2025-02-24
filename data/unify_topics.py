# %%
import pandas as pd
import xml.etree.cElementTree as et

topics_head = ['topic', 'query', 'cochranedoi', 'description', 'narrative']
xml_root = et.parse("./data/2019topics.xml")
rows = xml_root.findall('topic')
xml_data = [
    [int(row.find('number').text), row.find('query').text, row.find('cochranedoi').text,
     row.find('description').text, row.find('narrative').text] for row in rows]
topics2019 = pd.DataFrame(xml_data, columns=topics_head)
topics_answers = pd.read_csv("./data/2019topics_efficacy.txt", header=None, sep=' ',
                             names=['topic', 'efficacy'])
topics2019 = pd.merge(topics2019, topics_answers, how='left', on='topic')
# %%
topics2019["evidence"] = topics2019.cochranedoi.apply(lambda x: f"https://doi.org/{x}")

# %%
import pandas as pd
import xml.etree.cElementTree as et

topics_head = ['topic', 'query', 'evidence', 'description', 'narrative', 'stance']
xml_root = et.parse("./data/misinfo-2021-topics.xml")
rows = xml_root.findall('topic')
xml_data = [
    [int(row.find('number').text), row.find('query').text, row.find('evidence').text,
     row.find('description').text, row.find('narrative').text, row.find('stance').text] for row in rows]
topics_2021 = pd.DataFrame(xml_data, columns=topics_head)
topics_answers = pd.read_csv("./data/2019topics_efficacy.txt", header=None, sep=' ',
                             names=['topic', 'efficacy'])
topics_2021 = pd.merge(topics_2021, topics_answers, how='left', on='topic')
topics_2021["efficacy"] = topics_2021.stance.map({"helpful": 1, "unhelpful": -1})

#%%
import pandas as pd
import xml.etree.cElementTree as et

topics_head = ['topic', 'query', 'evidence', 'description', 'narrative', 'stance']
xml_root = et.parse("./data/misinfo-2022-topics.xml")
rows = xml_root.findall('topic')
xml_data = [
    [int(row.find('number').text), row.find('query').text, row.find('evidence').text,
     row.find('question').text, row.find('background').text, row.find('answer').text] for row in rows]
topics_2022 = pd.DataFrame(xml_data, columns=topics_head)
topics_2022["efficacy"] = float('nan')

# topics_answers = pd.read_csv("./data/2019topics_efficacy.txt", header=None, sep=' ',
#                              names=['topic', 'efficacy'])
# topics_2022 = pd.merge(topics_2021, topics_answers, how='left', on='topic')

# %%
final_columns = ['topic', 'query', 'evidence', 'description', 'narrative', 'efficacy']
topics: pd.DataFrame = pd.concat([
    topics2019[final_columns], topics_2021[final_columns], topics_2022[final_columns]
])


#%%
topics.to_csv("data/topics.tsv", index=False, sep="\t")
#%%
topics = pd.read_csv("data/topics_fixed.tsv.txt", sep="\t")

RW = pd.read_csv("./data/RW.txt", sep="\t")
RW = RW.rename(columns={"pubmed_url":"evidence"})
topics = pd.concat([topics,RW,topics_2022])
topics = topics.drop(columns=["stance"])
topics.to_csv("data/topics_fixed_extended.tsv.txt", index=False, sep="\t")