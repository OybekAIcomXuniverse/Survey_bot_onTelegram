#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#from urllib import response
#import Constants as keys
from telegram import *
from telegram.ext import *
import sqlite3
import datetime
import logging
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from itertools import compress
from telegram.ext.dispatcher import run_async
from io import BytesIO
from pandas import ExcelWriter

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

conn = sqlite3.connect('D:/Oybek/Python/Bot/Real sector/data/real_sector.db', check_same_thread=False)
cursor = conn.cursor()

global payload, language_dict, question_states_per_user, allowing_admin, allowing_agent
payload = {}
language_states = {}
question_states_per_user = {}
allowing_admin = {}
allowing_agent = {}

LANGUAGE, SECTOR, Q1, Q2, Q3, Q4, Q5, Q6_1, Q6_2, Q7, Q8, Q9, Q10, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q19,Q20, LAST1, LAST2 = range(25)

global r_but, r_but_f, sq_b, sq_b_f
r_but = '🔘'
r_but_f = '🔵'
sq_b = '🔲'
sq_b_f = '✅'


def answers(conn, questions: str):
    #conn = ensure_connection()
    c = conn.cursor()
    
    c.execute(f'SELECT question_id FROM {questions} ORDER BY question_id DESC LIMIT 1')
    for_range = c.fetchall()[0][0] + 1
    
    question_states = {}
    
    for i in range(1, for_range):
        c.execute(f'SELECT question FROM {questions} WHERE question_id = {i} LIMIT 1')
        question = c.fetchall()[0][0]
        
        c.execute(f'SELECT answer_id, answer, number_of_choices FROM {questions} WHERE question_id = {i}')
        answers = c.fetchall()
        answers_dict = {}
        for j in answers:
            if j[2] == 'one':
                answers_dict[j[0]] = r_but + ' ' + j[1]
            elif j[2] == 'multiple':
                answers_dict[j[0]] = sq_b + ' ' + j[1]
                
        question_states[question] = answers_dict
    return question_states

def insert_user(user:int, user_name:str, language:str, q1:int):
    pool = ['manufacturing_pool', 'construction_pool', 'service_pool', 'retail_pool'][q1-1]
    cursor.execute(f'INSERT INTO {pool} (user, user_name, language, q1) VALUES (?, ?, ?, ?)',                           (user, user_name, language, q1))
    conn.commit()

def update_answer(user:int, sector:int, question_num:int, answer:int):
    pool = ['manufacturing_pool', 'construction_pool', 'service_pool', 'retail_pool'][sector-1]
    cursor.execute(f'UPDATE {pool} SET q{question_num} = ? WHERE user = ?',                   (answer, user))
    conn.commit()
    
def update_time(user:int, sector:int, time:datetime.datetime):
    pool = ['manufacturing_pool', 'construction_pool', 'service_pool', 'retail_pool'][sector-1]
    cursor.execute(f'UPDATE {pool} SET time = ? WHERE user = ?',                   (time, user))
    conn.commit()
    
def delete_prev(user:int, sector:int):
    pool = ['manufacturing_pool', 'construction_pool', 'service_pool', 'retail_pool'][sector-1]
    cursor.execute(f'DELETE FROM {pool} WHERE user = {user}')
    conn.commit()
    
def func_last_question(user:int):
    pool_list = ['manufacturing_pool', 'construction_pool', 'service_pool', 'retail_pool']
    c = conn.cursor()
    c.execute(f'WITH t AS (SELECT user, time, q1 FROM {pool_list[0]} WHERE user = {user} UNION                          SELECT user, time, q1 FROM {pool_list[1]} WHERE user = {user} UNION                          SELECT user, time, q1 FROM {pool_list[2]} WHERE user = {user} UNION                          SELECT user, time, q1 FROM {pool_list[3]} WHERE user = {user})                          SELECT q1 FROM t ORDER BY time DESC LIMIT 1')
    sector = c.fetchall()[0][0]
    c.execute(f'SELECT * FROM {pool_list[sector-1]}')
    last_question_num = int(list(map(lambda x: x[0], c.description))[-1].replace('q', ''))
    sector_and_last_q_num = (sector, last_question_num)
    return sector_and_last_q_num

def which_language(user:int):
    pool_list = ['manufacturing_pool', 'construction_pool', 'service_pool', 'retail_pool']
    c = conn.cursor()
    c.execute(f'WITH t AS (SELECT user, time, language FROM {pool_list[0]} WHERE user = {user} UNION                          SELECT user, time, language FROM {pool_list[1]} WHERE user = {user} UNION                          SELECT user, time, language FROM {pool_list[2]} WHERE user = {user} UNION                          SELECT user, time, language FROM {pool_list[3]} WHERE user = {user})                          SELECT language FROM t ORDER BY time DESC LIMIT 1')
    language = c.fetchall()[0][0]
   
    return language

def alerting(text):
    if '|' in text:
        return text[:text.index('|')] + '</b>' + '\n' + text[text.index('|')+1:]
    else:
        return text + '</b>'

def is_user_trying_again(user:int, sector:int):
    pool_list = ['manufacturing_pool', 'construction_pool', 'service_pool', 'retail_pool']
    c = conn.cursor()
    pool = pool_list[sector-1]
    c.execute(f'SELECT * FROM {pool}')
    last_question = list(map(lambda x: x[0], c.description))[-2]
    c.execute(f'SELECT user FROM {pool} WHERE user = {user} AND {last_question} NOT NULL')
    try:
        if c.fetchall()[0][0]:
            return True
    except:
        return False
    
#Admin related functions----------------------------------------------------------------
def insert_admin(allowed_admin_id:int):
    cursor.execute('INSERT INTO allowed_admins (allowed_admin_id) VALUES (?)',                           ((allowed_admin_id,)))
    conn.commit()

def is_this_admin_allowed(allowed_id:int, conn):
    #conn = ensure_connection()
    c = conn.cursor()
    c.execute(f'SELECT allowed_admin_id FROM allowed_admins WHERE allowed_admin_id = {allowed_id} LIMIT 1')
    try:
        c.fetchall()[0][0]
        return True
    except:
        return False

def insert_agent(agent_id:int, region:str):
    cursor.execute('INSERT INTO allowed_agents (agent_id, region) VALUES (?, ?)',                           (agent_id, region))
    conn.commit()
    
def is_this_agent_allowed(allowed_id:int, conn):
    #conn = ensure_connection()
    c = conn.cursor()
    c.execute(f'SELECT * FROM allowed_agents WHERE agent_id = {allowed_id}')
    try:
        value = c.fetchall()[-1][-1]
        return value
    except:
        return False
#-------------------------------------------------------------------------------------------

def start_command(update, context):
    def start_func():
        keyboard =  [[InlineKeyboardButton("                  Ўзбекча                 ", callback_data='uz')],
                     [InlineKeyboardButton("                  Русский                 ", callback_data='ru')]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        payload[update.effective_chat.id] = {}
        payload[update.effective_chat.id]['started'] = True
        
        context.bot.send_message(chat_id=update.effective_chat.id, text='<b>Tilni tanlang/Выберите язык:</b>',                                 reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        
    #Delete admin allowing action
    try:
        del allowing_admin[update.effective_chat.id]
        start_func()
    except:
        try:
            del allowing_agent[update.effective_chat.id]
            start_func()
        except:
            start_func()
            
def query_handler(update, context):

    try:
        answer = update.callback_query.data
            
        if answer == 'uz':
            
            keyboard =  [[InlineKeyboardButton("                  Ўзбекча   ✔️           " , callback_data='uz')],
                         [InlineKeyboardButton("                  Русский                 ", callback_data='ru')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,                                                          message_id=update.effective_message.message_id, reply_markup=reply_markup)
            
            try:
                payload[update.effective_chat.id]['num']
                already_tapped = True
            except:
                already_tapped = False
                
            if already_tapped:
                start_del = update.effective_message.message_id + 1
                del_success = True
                while del_success:
                    try:
                        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=start_del)
                        start_del += 1
                        last_massage_id = start_del - 1
                    except:
                        try:
                            last_massage_id
                            del_success = False
                        except:
                            start_del += 1
            
            payload[update.effective_chat.id] = {'user':update.callback_query.from_user.id, 'language':answer}
            payload[update.effective_chat.id]['started'] = True
            to_next = 'Кейингиси  ➡️'
            notification = 'Вариантлардан бирини танланг'
    
            gratitute = '<b>Фикр билдирганингиз учун раҳмат!</b>'
                
            language_states[update.effective_chat.id] = {'to_next':to_next, 'notification':notification,                                                        'gratitute':gratitute}
            buttons_list = [r_but+' '+'Саноат', r_but+' '+'Қурилиш', r_but+' '+'Хизматлар', r_but+' '+'Савдо']
            payload[update.effective_chat.id]['buttons_list'] = buttons_list
            keyboard = [[InlineKeyboardButton(buttons_list[0], callback_data=1)], [InlineKeyboardButton(buttons_list[1], callback_data=2)],                        [InlineKeyboardButton(buttons_list[2], callback_data=3)], [InlineKeyboardButton(buttons_list[3], callback_data=4)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = 'Фаолоият соҳангиз:'
            payload[update.effective_chat.id]['num'] = 1
            
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'<b>{1}. '+text+'</b>',                                 reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            payload[update.effective_chat.id]['num']+=1
            
            
        elif answer == 'ru':
            
            keyboard =  [[InlineKeyboardButton("                  Ўзбекча                 ", callback_data='uz')],
                         [InlineKeyboardButton("                  Русский   ✔️            ", callback_data='ru')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,                                                          message_id=update.effective_message.message_id, reply_markup=reply_markup)
            
            try:
                payload[update.effective_chat.id]['num']
                already_tapped = True
            except:
                already_tapped = False
                
            if already_tapped:
                start_del = update.effective_message.message_id + 1
                del_success = True
                while del_success:
                    try:
                        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=start_del)
                        start_del += 1
                        last_massage_id = start_del - 1
                    except:
                        try:
                            last_massage_id
                            del_success = False
                        except:
                            start_del += 1
            
            payload[update.effective_chat.id] = {'user':update.callback_query.from_user.id, 'language':answer}
            payload[update.effective_chat.id]['started'] = True
            to_next = 'Следуший  ➡️'
            notification = 'Выберите один из вариантов'
    
            gratitute = '<b>Спасибо за ваши мнения!</b>'
                
            language_states[update.effective_chat.id] = {'to_next':to_next, 'notification':notification,                                                        'gratitute':gratitute}
            
            buttons_list = [r_but+' '+'Промышленность', r_but+' '+'Строительство', r_but+' '+'Услуги', r_but+' '+'Торговля']
            payload[update.effective_chat.id]['buttons_list'] = buttons_list
            keyboard = [[InlineKeyboardButton(buttons_list[0], callback_data=1)], [InlineKeyboardButton(buttons_list[1], callback_data=2)],                        [InlineKeyboardButton(buttons_list[2], callback_data=3)], [InlineKeyboardButton(buttons_list[3], callback_data=4)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = 'Сфера ваша деятельности:'
            payload[update.effective_chat.id]['num'] = 1
            
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'<b>{1}. '+text+'</b>',                                 reply_markup=reply_markup, parse_mode=ParseMode.HTML)
            payload[update.effective_chat.id]['num']+=1
        
        elif 'q' in answer:
            q_num = int(answer.replace('q', ''))
            n = payload[update.effective_chat.id]['num']
            if n - 2 >= q_num:
                text = 'Келган саволингиздан давом этинг/Продолжайте с последнего вопроса'
                context.bot.answer_callback_query(callback_query_id=update.callback_query.id, text=text)
            else:
                q = list(question_states_per_user[update.effective_chat.id].keys())[q_num-1]
                q_answers = question_states_per_user[update.effective_chat.id][q]
                answer_list = list(q_answers.values())
                if list(filter(lambda x: sq_b_f in x, answer_list)) == []:
                    notification=language_states[update.effective_chat.id]['notification']
                    context.bot.answer_callback_query(callback_query_id=update.callback_query.id, text=notification)
                else:
                    q_list = list(question_states_per_user[update.effective_chat.id].keys())
                    next_q_ind = q_list.index(q)+1
                    q_next = q_list[next_q_ind]
                    q_next_answers = question_states_per_user[update.effective_chat.id][q_next]
                    answer_list = list(q_next_answers.values())
                    key_list = list(q_next_answers.keys())
                    
                    try:
                        first_ins = answer_list[0]
                        keyboard = []
                        for i, j in zip(answer_list, key_list):
                            keyboard.append([InlineKeyboardButton(i, callback_data=j)])
                        
                        if sq_b in first_ins:
                            keyboard.append([InlineKeyboardButton(language_states[update.effective_chat.id]['to_next'],                                                              callback_data=f'q{next_q_ind+1}')])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        context.bot.send_message(chat_id=update.effective_chat.id, text=f'<b>{n}. ' +alerting(q_next),                                                 reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                    except:    
                        payload[update.effective_chat.id]['text_question'] = q_next
                        context.bot.send_message(chat_id=update.effective_chat.id, text=f'<b>{n}. ' + alerting(q_next),                                                 parse_mode=ParseMode.HTML)
                                    
                    payload[update.effective_chat.id]['num']+=1
        
        # For admin ----------------------------------------------------------------------   
        elif 'add_admin' in answer:
            try:
                del payload[update.effective_chat.id]
                del language_states[update.effective_chat.id]
                del question_states_per_user[update.effective_chat.id]
                context.bot.send_message(chat_id=update.effective_chat.id, text='<b>Янги админ "id"сини юборинг:</b>',                                 parse_mode=ParseMode.HTML)
            except:
                context.bot.send_message(chat_id=update.effective_chat.id, text='<b>Янги админ "id"сини юборинг:</b>',                                 parse_mode=ParseMode.HTML)
            try:
                del allowing_agent[update.effective_chat.id]
                allowing_admin[update.effective_chat.id] = 'started'
            except:
                allowing_admin[update.effective_chat.id] = 'started'
        elif 'regions_stat' in answer:
            from regions import regions  
            #regions()
            #image = open('D:/Oybek/regions.png', 'rb')
            image = regions()
            plot_file = BytesIO()
            image.savefig(plot_file, format='png', bbox_inches='tight', dpi=150)
            plot_file.seek(0)
            if image:
                context.bot.sendMediaGroup(chat_id=update.effective_chat.id, media=[InputMediaPhoto(plot_file, caption="")])
        elif 'pools' in answer:
            from general_pool import general_pool
            plot_file = general_pool()
            if plot_file:
                context.bot.send_document(chat_id=update.effective_chat.id, document=plot_file,                                           filename='general_pool.xlsx', caption="")
        elif 'add_agent' in answer:
            regions = ['Тошкент шаҳри',
               'Хоразм вилояти',
               'Қашқадарё вилояти',
               'Сирдарё вилояти',
               'Наманган вилояти',
               'Қорақалпоғистон Республикаси',
               'Андижон вилояти',
               'Самарқанд вилояти', 
               'Бухоро вилояти',
               'Тошкент вилояти',
               'Жиззах вилояти',
               'Сурхондарё вилояти',
               'Навоий вилояти',
               'Фарғона вилояти']
    
            
            regions_emoji = list(map(lambda x: r_but + ' ' + x, regions))
            
            keyboard = []
            for i in range(0, 14, 2):
                buttons = [InlineKeyboardButton(regions_emoji[i], callback_data=i+0.1),                           InlineKeyboardButton(regions_emoji[i+1], callback_data=i+1+0.1)]
                keyboard.append(buttons) 
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            context.bot.send_message(chat_id=update.effective_chat.id, text='Вилоятни танланг:',                                     reply_markup=reply_markup)
        elif float(answer) in list(map(lambda x: x+0.1, list(range(14)))):
            regions = ['Тошкент шаҳри',
               'Хоразм вилояти',
               'Қашқадарё вилояти',
               'Сирдарё вилояти',
               'Наманган вилояти',
               'Қорақалпоғистон Республикаси',
               'Андижон вилояти',
               'Самарқанд вилояти', 
               'Бухоро вилояти',
               'Тошкент вилояти',
               'Жиззах вилояти',
               'Сурхондарё вилояти',
               'Навоий вилояти',
               'Фарғона вилояти']
            
            regions_emoji = list(map(lambda x: r_but + ' ' + x, regions))
            answer = regions_emoji[int(float(answer))]
            
            def replace_emoji(x):
                if answer in x:
                    return x.replace(r_but, r_but_f)
                else:
                    return x
                   
            regions_emoji2 = list(map(replace_emoji, regions_emoji))
            
            keyboard = []
            for i in range(0, 14, 2):
                buttons = [InlineKeyboardButton(regions_emoji2[i], callback_data=i+0.1),                           InlineKeyboardButton(regions_emoji2[i+1], callback_data=i+1+0.1)]
                keyboard.append(buttons) 
            reply_markup = InlineKeyboardMarkup(keyboard)
    
            context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,                                                      message_id=update.effective_message.message_id, reply_markup=reply_markup)
            
            context.bot.send_message(chat_id=update.effective_chat.id, text='Вилоятдаги агентнинг телеграм "id"сини юборинг.')
            allowing_agent[update.effective_chat.id] = {}
            
            try:
                del allowing_admin[update.effective_chat.id]
                allowing_agent[update.effective_chat.id]['region'] = answer.replace(f'{r_but} ', '')
            except:
                allowing_agent[update.effective_chat.id]['region'] = answer.replace(f'{r_but} ', '')
        # ---------------------------------------------------------------------------------       
        
        elif int(answer) in [1, 2, 3, 4]:
            if is_user_trying_again(update.effective_chat.id, int(answer)):
                language = payload[update.effective_chat.id]['language']
                if language == 'uz':
                    text = 'Сиз ушбу сўровномада қатнашиб бўлдингиз,\nкейинги ойдаги сўровномада кўришгунча.'
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                if language == 'ru':
                    text = 'Вы уже участвовали в этом опросе,\nдо встречи в следующих опросах в следующем месяце!'
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            else:    
                language = payload[update.effective_chat.id]['language']
                #query = update.callback_query
                payload[update.effective_chat.id]['sector'] = int(answer)
                
                buttons_list = payload[update.effective_chat.id]['buttons_list']
                
                delete_prev(update.effective_chat.id, int(answer))
                insert_user(update.effective_chat.id, update.callback_query.from_user.username, language, int(answer))
                
                if sum(list(map(lambda x: r_but_f in x, buttons_list))) >= 1:
                    buttons_list = list(map(lambda x: x.replace(r_but_f, r_but), buttons_list))
                    already_tapped = True
                else:
                    already_tapped = False
                    
                buttons_list[int(answer)-1] = buttons_list[int(answer)-1].replace(r_but, r_but_f)
                payload[update.effective_chat.id]['buttons_list'] = buttons_list
                keyboard = [[InlineKeyboardButton(buttons_list[0], callback_data=1)], [InlineKeyboardButton(buttons_list[1], callback_data=2)],                            [InlineKeyboardButton(buttons_list[2], callback_data=3)], [InlineKeyboardButton(buttons_list[3], callback_data=4)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,                                                              message_id=update.effective_message.message_id, reply_markup=reply_markup)
                if already_tapped:
                    start_del = update.effective_message.message_id + 1
                    del_success = True
                    while del_success:
                        try:
                            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=start_del)
                            start_del += 1
                            last_massage_id = start_del - 1
                        except:
                            try:
                                last_massage_id
                                del_success = False
                            except:
                                start_del += 1
                    payload[update.effective_chat.id]['num'] = 2
                            
                if language == 'uz':
                    if int(answer) == 1:
                        question_states = answers(conn, questions='manufacturing_questions_uz')
                    elif int(answer) == 2:
                        question_states = answers(conn, questions='construction_questions_uz')
                    elif int(answer) == 3:
                        question_states = answers(conn, questions='service_questions_uz')
                    elif int(answer) == 4:
                        question_states = answers(conn, questions='retail_questions_uz')
                elif language == 'ru':
                    if int(answer) == 1:
                        question_states = answers(conn, questions='manufacturing_questions_ru')
                    elif int(answer) == 2:
                        question_states = answers(conn, questions='construction_questions_ru')
                    elif int(answer) == 3:
                        question_states = answers(conn, questions='service_questions_ru')
                    elif int(answer) == 4:
                        question_states = answers(conn, questions='retail_questions_ru')
            
                question_states_per_user[update.effective_chat.id] = question_states
                
                question_dict = {}
                for i in question_states.keys():
                    for j in question_states[i].keys():
                        question_dict[j] = i
                
                payload[update.effective_chat.id]['question_dict'] = question_dict
            
                q = list(question_states.keys())[1]
                q_answers = question_states[q]
                answer_list = list(q_answers.values())
                key_list = list(q_answers.keys())
                
                keyboard = []
                for i, j in zip(answer_list, key_list):
                    keyboard.append([InlineKeyboardButton(i, callback_data=j)])
                
                if sq_b in answer_list[0]:
                    keyboard.append([InlineKeyboardButton(language_states[update.effective_chat.id]['to_next'], callback_data='q2')])
                    
                reply_markup = InlineKeyboardMarkup(keyboard)
                n = payload[update.effective_chat.id]['num']
                context.bot.send_message(chat_id=update.effective_chat.id, text=f'<b>{n}. ' + alerting(q),                                         reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                payload[update.effective_chat.id]['num']+=1
        
        else:
            question_dict = payload[update.effective_chat.id]['question_dict']
            
            q = question_dict[int(answer)]
            
            q_answers = question_states_per_user[update.effective_chat.id][q]
            answer_list = list(q_answers.values())
            if (sq_b in answer_list[0]) or (sq_b_f in answer_list[0]):
                q_num = list(question_states_per_user[update.effective_chat.id].keys()).index(q)+1
                n = payload[update.effective_chat.id]['num']
                if n - 2 >= q_num:
                    if sq_b in q_answers[int(answer)]:
                        q_answers[int(answer)] = q_answers[int(answer)].replace(sq_b, sq_b_f)
                        key_list = list(q_answers.keys())
                        answer_list = list(q_answers.values())
                        keyboard = []
                        for i, j in zip(answer_list, key_list):
                            keyboard.append([InlineKeyboardButton(i, callback_data=j)])
                        
                        q_list = list(question_states_per_user[update.effective_chat.id].keys())
                        q_ind = q_list.index(q)+1
                        if (sq_b in answer_list[0]) or (sq_b_f in answer_list[0]):
                            keyboard.append([InlineKeyboardButton(language_states[update.effective_chat.id]['to_next'],                                                                  callback_data=f'q{q_ind}')])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                
                        context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,                                                                  message_id=update.effective_message.message_id, reply_markup=reply_markup)
                    else:
                        answer_list = list(q_answers.values())
                        if sum(list(map(lambda x: sq_b_f in x, answer_list))) == 1:
                            text = 'Ҳеч бўлмаганда 1 та вариант белгилансин/Выберите хотя бы 1 вариант'
                            context.bot.answer_callback_query(callback_query_id=update.callback_query.id, text=text)
                        else:
                            q_answers[int(answer)] = q_answers[int(answer)].replace(sq_b_f, sq_b)
                    
                            key_list = list(q_answers.keys())
                            answer_list = list(q_answers.values())
                            keyboard = []
                            for i, j in zip(answer_list, key_list):
                                keyboard.append([InlineKeyboardButton(i, callback_data=j)])
                            
                            q_list = list(question_states_per_user[update.effective_chat.id].keys())
                            q_ind = q_list.index(q)+1
                            if (sq_b in answer_list[0]) or (sq_b_f in answer_list[0]):
                                keyboard.append([InlineKeyboardButton(language_states[update.effective_chat.id]['to_next'],                                                                      callback_data=f'q{q_ind}')])
                            reply_markup = InlineKeyboardMarkup(keyboard)
                    
                            context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,                                                                      message_id=update.effective_message.message_id, reply_markup=reply_markup)
                                    
                else:    
                    if sq_b in q_answers[int(answer)]:
                        q_answers[int(answer)] = q_answers[int(answer)].replace(sq_b, sq_b_f)
                    else:
                        q_answers[int(answer)] = q_answers[int(answer)].replace(sq_b_f, sq_b)
                    
                    key_list = list(q_answers.keys())
                    answer_list = list(q_answers.values())
                    keyboard = []
                    for i, j in zip(answer_list, key_list):
                        keyboard.append([InlineKeyboardButton(i, callback_data=j)])
                    
                    q_list = list(question_states_per_user[update.effective_chat.id].keys())
                    q_ind = q_list.index(q)+1
                    if (sq_b in answer_list[0]) or (sq_b_f in answer_list[0]):
                        keyboard.append([InlineKeyboardButton(language_states[update.effective_chat.id]['to_next'],                                                              callback_data=f'q{q_ind}')])
                    reply_markup = InlineKeyboardMarkup(keyboard)
            
                    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,                                                              message_id=update.effective_message.message_id, reply_markup=reply_markup)
             #insert multiple choice answers into the database:   
                filt = list(map(lambda x: sq_b_f in x, q_answers.values()))
                ticked_answers = f'{list(compress(q_answers.keys(), filt))}'
                sector = payload[update.effective_chat.id]['sector']
                update_answer(update.effective_chat.id, sector, q_num, ticked_answers)
            
            else:
                if sum(list(map(lambda x: r_but_f in x, answer_list))) >= 1:
                    ind = list(map(lambda x: r_but_f in x, answer_list)).index(True)
                    key_list = list(q_answers.keys())
                    q_answers[key_list[ind]] = q_answers[key_list[ind]].replace(r_but_f, r_but)
                    already_tapped = True
                else:
                    already_tapped = False
                
                q_answers[int(answer)] = q_answers[int(answer)].replace(r_but, r_but_f)
                answer_list = list(q_answers.values())
                key_list = list(q_answers.keys())
                                            
                keyboard = []
                for i, j in zip(answer_list, key_list):
                    keyboard.append([InlineKeyboardButton(i, callback_data=j)])     
            
                reply_markup = InlineKeyboardMarkup(keyboard)
        
                context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,                                                          message_id=update.effective_message.message_id, reply_markup=reply_markup)
        
                '''
                db_table_val(user=query.from_user.id, user_name=query.from_user.username,\
                                     language=language, question=q1, answer=region, date=query.message.date)
                '''
                
                if not already_tapped:
                    q_list = list(question_states_per_user[update.effective_chat.id].keys())
                    next_q_ind = q_list.index(q)+1
                    q_next = q_list[next_q_ind]
                    q_next_answers = question_states_per_user[update.effective_chat.id][q_next]
                    answer_list = list(q_next_answers.values())
                    key_list = list(q_next_answers.keys())
                    
                    n = payload[update.effective_chat.id]['num']
                    try:
                        first_ins = answer_list[0]
                        keyboard = []
                        for i, j in zip(answer_list, key_list):
                            keyboard.append([InlineKeyboardButton(i, callback_data=j)])
                        
                        if sq_b in first_ins:
                            keyboard.append([InlineKeyboardButton(language_states[update.effective_chat.id]['to_next'],                                                              callback_data=f'q{next_q_ind+1}')])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        context.bot.send_message(chat_id=update.effective_chat.id, text=f'<b>{n}. ' + alerting(q_next),                                                 reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                    except:    
                        payload[update.effective_chat.id]['text_question'] = q_next
                        context.bot.send_message(chat_id=update.effective_chat.id, text=f'<b>{n}. ' + alerting(q_next),                                                 parse_mode=ParseMode.HTML)
                                                        
                    payload[update.effective_chat.id]['num']+=1
                    
                    if next_q_ind == len(q_list)-1:
                        
                            sector = payload[update.effective_chat.id]['sector']
                            update_time(update.effective_chat.id, sector, update.callback_query.message.date)
                            
                            q_list = list(question_states_per_user[update.effective_chat.id].keys())
                            q_num = q_list.index(q)+1
                            sector = payload[update.effective_chat.id]['sector']
                            update_answer(update.effective_chat.id, sector, q_num, int(answer))
                            
                            del question_states_per_user[update.effective_chat.id]
                            del language_states[update.effective_chat.id]
                            del payload[update.effective_chat.id]
            
                try:
                    q_list = list(question_states_per_user[update.effective_chat.id].keys())
                    q_num = q_list.index(q)+1
                    sector = payload[update.effective_chat.id]['sector']
                    update_answer(update.effective_chat.id, sector, q_num, int(answer))
                except:
                    text = 'Охирги савол/Последний вопрос'
                    context.bot.answer_callback_query(callback_query_id=update.callback_query.id, text=text)
            
    except:
        text = 'Oooops!'
        context.bot.answer_callback_query(callback_query_id=update.callback_query.id, text=text)
         
                
def handle_message(update, context):
    text_answer = str(update.message.text)
    try:
        region = allowing_agent[update.effective_chat.id]['region']
        try:
            agent_id = int(update.message.text)
            insert_agent(agent_id, region)
            del allowing_agent[update.effective_chat.id]
            text = f'{region}га агент {agent_id} бириктирилди.'
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        except:
            text = 'Илтимос, рақам жўнатинг!'
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    except:
        
        try:
            started_status = allowing_admin[update.effective_chat.id]
            try:
                survey_process = payload[update.effective_chat.id]['started']
                text = 'Сўровномани якунлаб, кейин мурожаат қилинг.'
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                del allowing_admin[update.effective_chat.id]
            except:
                try:
                    insert_admin(int(update.message.text))
                    text = 'Янги админ қўшилди.'
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                    text = 'Табриклайман, сиз ҳам админ бўлдингиз.'
                    context.bot.send_message(chat_id=int(update.message.text), text=text)
                    del allowing_admin[update.effective_chat.id]
                except:
                    text = 'Илтимос, "id" рақамларда иборат бўлади!'
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
               
        except:
            try:
                q = payload[update.effective_chat.id]['text_question']
                q_list = list(question_states_per_user[update.effective_chat.id].keys())
                next_q_ind = q_list.index(q)+1
                
                def next_question():
                    q_next = q_list[next_q_ind]
                    q_next_answers = question_states_per_user[update.effective_chat.id][q_next]
                    answer_list = list(q_next_answers.values())
                    key_list = list(q_next_answers.keys())
                    
                    n = payload[update.effective_chat.id]['num']
                    try:
                        first_ins = answer_list[0]
                        keyboard = []
                        for i, j in zip(answer_list, key_list):
                            keyboard.append([InlineKeyboardButton(i, callback_data=j)])
                        if sq_b in first_ins:
                                        keyboard.append([InlineKeyboardButton(language_states[update.effective_chat.id]['to_next'],                                                                              callback_data=f'q{next_q_ind+1}')])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        context.bot.send_message(chat_id=update.effective_chat.id, text=f'<b>{n}. '+q_next+'</b>',                                             reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                    except:    
                        payload[update.effective_chat.id]['text_question'] = q_next
                        context.bot.send_message(chat_id=update.effective_chat.id, text=f'<b>{n}. ' + alerting(q_next),                                                 parse_mode=ParseMode.HTML)
                        
                    payload[update.effective_chat.id]['num']+=1
                    
                    q_num = q_list.index(q)+1
                    sector = payload[update.effective_chat.id]['sector']
                    update_answer(update.effective_chat.id, sector, q_num, text_answer)
                    
                    if next_q_ind == len(q_list)-1:
                        sector = payload[update.effective_chat.id]['sector']
                        update_time(update.effective_chat.id, sector, update.message.date)
                        
                        del question_states_per_user[update.effective_chat.id]
                        del language_states[update.effective_chat.id]
                        del payload[update.effective_chat.id]
                                
                if next_q_ind == payload[update.effective_chat.id]['num']-1:
                    
                    if 'телефон' in q:
                        num = [int(i) for i in list(text_answer) if i.isdigit()]
                        if len(num) < 9:
                            text = 'Илтимос, телефонингизни тўғри ва коди билан ёзинг!\nПожалуйста, напишите свой телефон правильно и с кодом!'
                            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                        else:
                            next_question()
                    elif 'СТИР' in q:
                        num = [int(i) for i in list(text_answer) if i.isdigit()]
                        if len(num) != 9:
                            text = 'Илтимос, СТИР рақамини тўғри ёзинг!\nПожалуйста, введите номер СТИР правильно!'
                            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                        else:
                            next_question()
                    else:
                        next_question()
                        
                else:
                    text = language_states[update.effective_chat.id]['notification']
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            except:
                view_text_uz = '<b>Сўровномада қатнашганингиз учун миннатдорчилик билдирамиз! Сизнинг фикрларингиз биз учун муҳим.</b>\nСўров натижалари бўйича маълумот Марказий банкнинг ижтимоий тармоқларидаги расмий саҳифаларида эълон қилинади (<a href="http://fb.com/centralbankuzbekistan/">Facebook</a>, <a href="http://instagram.com/centralbankuzbekistan/">Instagram</a>, Телеграм).\nАлоқа учун:\nтель: 71-233-00-65\nэлектрон почта: <a href="//mailto:info@cbu.uz">info@cbu.uz</a>)'
        
                view_text_ru = '<b>Спасибо за участие в опросе! Ваше мнение очень важно для нас.</b>\nИнформация о результатах опроса будет опубликована на официальных страницах Центрального банка в социальных сетях (<a href="http://fb.com/centralbankuzbekistan/">Facebook</a>, <a href="http://instagram.com/centralbankuzbekistan/">Instagram</a>, Телеграм).\nДля связи:\nтель: 71-233-00-65\nэлектронная почта: <a href="//mailto:info@cbu.uz">info@cbu.uz</a>)'
                
                try:
                    if payload[update.effective_chat.id]['started'] == True:
                        text = 'Вариантлардан бирини танланг\nВыберите один из вариантов'
                        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                except:
                    if which_language(update.effective_chat.id) == 'uz':
                        text = view_text_uz
                        context.bot.send_message(chat_id=update.effective_chat.id, text=text,                                                         parse_mode=ParseMode.HTML)
                    elif which_language(update.effective_chat.id) == 'ru':
                        text = view_text_ru
                        context.bot.send_message(chat_id=update.effective_chat.id, text=text,                                                         parse_mode=ParseMode.HTML)
                    
                    else:
                        text = 'Вариантлардан бирини танланг\nВыберите один из вариантов'
                        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                               
                    sector = func_last_question(update.effective_chat.id)[0]
                    q_num =  func_last_question(update.effective_chat.id)[1]
                    update_answer(update.effective_chat.id, sector, q_num, text_answer)
      
        
def admin_command(update, context):
    if is_this_admin_allowed(update.effective_chat.id, conn):
        keyboard =  [[InlineKeyboardButton("Админ қўшиш", callback_data='add_admin')],
                     [InlineKeyboardButton("Вилоятлар бўйича статистика", callback_data='regions_stat')],
                     [InlineKeyboardButton("Натижаларни жадвал кўринишида олиш", callback_data='pools')],
                     [InlineKeyboardButton("Вилоятлардаги агентга рухсат бериш", callback_data='add_agent')]]
    
        reply_markup = InlineKeyboardMarkup(keyboard)
           
        try:
            del payload[update.effective_chat.id]
            del language_states[update.effective_chat.id]
            del question_states_per_user[update.effective_chat.id]
            context.bot.send_message(chat_id=update.effective_chat.id, text='<b>Commands:</b>',                                 reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except:
            context.bot.send_message(chat_id=update.effective_chat.id, text='<b>Commands:</b>',                                 reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        text = 'Сиз админ эмассиз.'
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)    
        
def excel_stat_for_region_agents(update, context):
    region = is_this_agent_allowed(update.effective_chat.id, conn)
    if region:
        from excel_stat_for_agent import excel_stat_for_agent
        plot_file = excel_stat_for_agent(region)
        if plot_file:
            context.bot.send_document(chat_id=update.effective_chat.id, document=plot_file,                                       filename=f'{region}.xlsx', caption="")
            if update.effective_chat.id == 1193481074:
                text = 'Odiljonga Oybekdan salooom!'
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            
    else:
        text = 'Сизга руҳсат этилмаган, админга мурожаат қилинг.'
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

def text_stat_for_region_agents(update, context):
    region = is_this_agent_allowed(update.effective_chat.id, conn)
    if region:
        from text_stat_for_agent import text_stat_for_agent
        field_texts = text_stat_for_agent(region)
        for i in field_texts:
            context.bot.send_message(chat_id=update.effective_chat.id, text=i)

def for_allowed_command(update, context):
    regions = ['Тошкент шаҳри',
               'Хоразм вилояти',
               'Қашқадарё вилояти',
               'Сирдарё вилояти',
               'Наманган вилояти',
               'Қорақалпоғистон Республикаси',
               'Андижон вилояти',
               'Самарқанд вилояти', 
               'Бухоро вилояти',
               'Тошкент вилояти',
               'Жиззах вилояти',
               'Сурхондарё вилояти',
               'Навоий вилояти',
               'Фарғона вилояти']
    
    global regions_emoji
    regions_emoji = list(map(lambda x: r_but + ' ' + x, regions))
    
    keyboard = []
    for i in range(0, 14, 2):
        buttons = [InlineKeyboardButton(regions_emoji[i], callback_data=i+0.1),                   InlineKeyboardButton(regions_emoji[i+1], callback_data=i+1+0.1)]
        keyboard.append(buttons) 
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text='add region:',                             reply_markup=reply_markup)

'''
def please_refill(update, context):
    from please_refill import please_refill
    unfinished = please_refill()
    for i in unfinished:
        context.bot.send_message(chat_id=i, text='Агар сўровномани якунламаган бўлсангиз, илтимос, "меню"даги "Бекор қилиш" буйруғини босиб, сўровномани якунига етказишингиз мумкин.')
        break
'''
def cancel(update, context):
    try:
        del payload[update.effective_chat.id]
        del language_states[update.effective_chat.id]
        del question_states_per_user[update.effective_chat.id]
        text = 'Бекор қилинди.\nОтменен.'
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)        
    except:
        text = 'Бекор қилинди.\nОтменен.'
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    updater = Updater("5188342456:AAH-vLblIOp47FXbMsNyWyyVeNv8c6QD9Oc", use_context=True, workers=2)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start_command))
    #dp.add_handler(CallbackQueryHandler(admin_query_handler))
    dp.add_handler(CallbackQueryHandler(query_handler))
    #dp.add_handler(CallbackQueryHandler(admin_query_handler))
    dp.add_handler(CommandHandler('admin', admin_command))
    dp.add_handler(CommandHandler('cancel', cancel))
    #dp.add_handler(CommandHandler('finished_per_region_77', finished_per_region_command))
    dp.add_handler(CommandHandler('excel_stat_for_region_agents', excel_stat_for_region_agents))
    dp.add_handler(CommandHandler('text_stat_for_region_agents', text_stat_for_region_agents))
    #dp.add_handler(CommandHandler('please_refill_77', please_refill))
  
    dp.add_handler(MessageHandler(Filters.text, handle_message))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()


# In[ ]:




