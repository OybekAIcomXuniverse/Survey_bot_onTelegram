#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
import sqlite3
import datetime
from sqlalchemy.types import Integer
import os
list_data = os.listdir('D:/Oybek/Python/Bot/Real sector/excel_files/')
conn = sqlite3.connect('D:/Oybek/Python/Bot/Real sector/data/real_sector.db', check_same_thread=False)
for i in list_data:
    questions = pd.read_excel(f'D:/Oybek/Python/Bot/Real sector/excel_files/{i}')
    questions.question = questions.question.str.strip()
    questions.answer = questions.answer.str.strip()
    questions.drop(['question_id','answer_id'], axis=1, inplace=True, errors='ignore')
    questions.index = range(1, questions.shape[0]+1)
    questions.reset_index(inplace=True)
    questions.rename(columns={'index':'answer_id'}, inplace=True)
    questions.answer_id = questions.answer_id.astype(int)
    
    df_question_id = questions[['question']].drop_duplicates().dropna().reset_index(drop=True)
    df_question_id.index = range(1, df_question_id.size+1)
    df_question_id.reset_index(inplace=True)
    df_question_id = df_question_id[['question', 'index']]
    df_question_id.set_index('question', inplace=True)
    questions = questions.join(df_question_id, on='question')
    questions.rename(columns={'index':'question_id'}, inplace=True)
    questions.question_id = questions.question_id.astype(int)
    questions = questions[['question_id', 'question', 'answer', 'number_of_choices', 'answer_id']]
    questions.to_excel(f'D:/Oybek/Python/Bot/Real sector/excel_files/{i}', index=False)
    questions.to_csv(f'D:/Oybek/Python/Bot/Real sector/csv_files/{i.replace("xlsx", "csv")}', index=False)
    questions.to_sql(name=i.replace('.xlsx', ''), if_exists='replace', index=False, con=conn)
    columns = list(map(lambda x: 'q'+str(x), list(questions.question_id.unique())))
    columns=['user', 'user_name', 'language', 'time'] + columns
    pool_data = pd.DataFrame(columns=columns)
    pool_data = pool_data.astype(int)
    pool_data.time = pd.to_datetime(pool_data.time)
    pool_data.to_sql(name=i[:i.index('_')]+'_pool', index=False, if_exists='replace', con=conn)

df = pd.read_excel('D:/Oybek/Python/Bot/Real sector/regions_norm.xlsx')
df.to_csv('D:/Oybek/Python/Bot/Real sector/regions_norm.csv', index=False)

