#!/usr/bin/env python
# coding: utf-8

# In[ ]:


def regions():
    
    import sqlite3
    import pandas as pd
    import matplotlib.pyplot as plt
    import ast
    conn = sqlite3.connect('D:/Oybek/Python/Bot/Real sector/data/real_sector.db', check_same_thread=False)
    cursor = conn.cursor()
    
    def into_int(x):
        try:
            value = int(x)
            return value
        except:
            return x
        
    gen_cols = pd.Series(['user', 'user_name', 'language', 'time'])
    
    pool_list = ['manufacturing_pool', 'construction_pool', 'service_pool', 'retail_pool']
    
    df_list = []
    for i in pool_list:
        df = pd.read_sql_query(f'SELECT * FROM {i}', conn)
        df = df.fillna(0).applymap(into_int)
        questions_df = pd.read_csv(f'D:/Oybek/Python/Bot/Real sector/csv_files/{i[:i.index("_")]}_questions_uz.csv')
        df.columns = pd.concat([gen_cols, questions_df.question.drop_duplicates()])
        answer_df = questions_df[['answer_id', 'answer']].set_index('answer_id')
        
        def convert_answer(x):
            try:
                value = answer_df.loc[x, 'answer']
                return value
            except:
                try:
                    answer_ids = ast.literal_eval(x)
                    value = ', '.join(answer_df.loc[answer_ids, 'answer'].to_list())
                    return value
                except:
                    return x
        
        df = df.applymap(convert_answer)
        
        df_list.append(df)
    
    manufacturing = df_list[0]
    final_q = manufacturing.columns[-2]
    region_q = 'Фаолият юритаётган ҳудуд (вилоят):'
    manufacturing_stat_reg = manufacturing[manufacturing[final_q] != 0][[region_q, final_q]].groupby([region_q]).count().reset_index()
    manufacturing_stat_reg.columns = ['region', 'manufacturing']
    manufacturing_stat_reg.set_index('region', inplace=True)
    
    construction = df_list[1]
    final_q = construction.columns[-2]
    region_q = 'Фаолият юритаётган ҳудуд (вилоят):'
    construction_stat_reg = construction[construction[final_q] != 0][[region_q, final_q]].groupby([region_q]).count().reset_index()
    construction_stat_reg.columns = ['region', 'construction']
    construction_stat_reg.set_index('region', inplace=True)
    
    service = df_list[2]
    final_q = service.columns[-2]
    region_q = 'Фаолият юритаётган ҳудуд (вилоят):'
    service_stat_reg = service[service[final_q] != 0][[region_q, final_q]].groupby([region_q]).count().reset_index()
    service_stat_reg.columns = ['region', 'service']
    service_stat_reg.set_index('region', inplace=True)
    
    retail = df_list[3]
    final_q = retail.columns[-2]
    region_q = 'Фаолият юритаётган ҳудуд (вилоят):'
    retail_stat_reg = retail[retail[final_q] != 0][[region_q, final_q]].groupby([region_q]).count().reset_index()
    retail_stat_reg.columns = ['region', 'retail']
    retail_stat_reg.set_index('region', inplace=True)
    
    general_stat = pd.read_csv('D:/Oybek/Python/Bot/Real sector/regions_norm.csv')
    general_stat = general_stat.join(manufacturing_stat_reg, on='region')
    general_stat = general_stat.join(construction_stat_reg, on='region')
    general_stat = general_stat.join(service_stat_reg, on='region')
    general_stat = general_stat.join(retail_stat_reg, on='region')
    general_stat['sum'] = general_stat.iloc[:, 2:].sum(axis=1)
    general_stat = general_stat[['region', 'manufacturing', 'construction', 'service', 'retail', 'sum', 'norm']]
    general_stat['bajardi_foizda'] = general_stat["sum"]*100/general_stat.norm
    general_stat['label'] = (general_stat["sum"]*100/general_stat.norm).apply(lambda x: f'{int(x)} %') + \
    general_stat["sum"].astype(int).astype(str).apply(lambda x: f' ({x} та)')
    general_stat.sort_values(by=['bajardi_foizda'], ascending=False, inplace=True)
    general_stat.index = range(1, general_stat.index.size+1)
    
    fig, ax = plt.subplots()
    hbars = ax.barh(general_stat.region, general_stat['bajardi_foizda'].to_list(), color = '#33adff')
    
    ax.invert_yaxis()  # labels read top-to-bottom
    
    for i, v in enumerate(general_stat['label']):
        ax.text(int(v[:v.index(' ')]) + 2, i, str(v), color='black', fontweight='bold', fontsize=8, ha='left', va='center')
    
    finished = int(general_stat['sum'].sum())
    ax.set_title(f'Ҳудудлар бўйича сўровноманинг бажарилиши фоизда\n         (жами {finished} та)', pad=30)
    ax.spines['right'].set_color('white')
    ax.spines['top'].set_color('white')
        
    #fig.savefig('D:/Oybek/regions.png', bbox_inches='tight', dpi=200)
    return fig

