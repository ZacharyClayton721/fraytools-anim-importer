## Fraytools Animation Importer V.9
## Created by: Zardy Z

print("Fraytools Animation Importer V.9")
print("By: Zardy Z")

import os
import shutil
import json
import uuid

from codecs import encode

import PySimpleGUI as sg

import sys

from PIL import Image, ImageChops

cwd = os.getcwd()

def myexcepthook(type,value,traceback,oldhook=sys.excepthook):
    oldhook(type,value,traceback)
    print(oldhook)
    print('A backup of all animation name changes can be found at\n'+os.path.join(cwd,'Files','System','Backup Anims.json'))
    input("Press Enter to Close...")

sys.excepthook = myexcepthook

'''File Handling Functions'''

'''Read file contents from given path'''
def readFile(path: str):
    with open(path, 'r', encoding='utf8', errors='ignore') as file:
        return file.readlines()

'''Write anim_indexes'''
def writeAnimIndexes(anim_indexes: list, path:str):
    anim_json = {}
    count = 0
    for a in anim_indexes:
        anim_json[count] = a
        count += 1

    writeNewCE(anim_json,path)


'''Reading the Imported names from the User'''
def getImportNames(path: str):
    data = getJSONData(path)

    anim_indexes = []
    for k,v in data.items():
        anim_indexes.append(v)

    return anim_indexes

def writeNewCE(ce_data,path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(ce_data, f, ensure_ascii=False, indent=4)

'''Read JSON contents from given path'''
def getJSONData(path: str):
    with open(path,'r') as file:
        return json.load(file)


'''Input Validation Functions'''

'''Checks file exists'''
def checkFile(path:str):
    if os.path.isfile(path):
        return True
    else:
        if path == '':
            sg.popup('Please Provide a File Path!')
            return False
        else:
            sg.popup(path+' does not exist! Please choose a valid file!!')
            return False

'''Checks folder exists'''
def checkFolder(path:str):
    if os.path.exists(path):
        return True
    else:
        if path == '':
            sg.popup('Please Provide a Folder Path!')
            return False
        else:
            sg.popup(path+' does not exist! Please choose a valid folder!!')
            return False

def getSettings():
    return getJSONData(settings_path)


default_names = readFile('Files\\System\\Default Anims.txt')
default_names = default_names[0].split(',')
current_path = os.path.abspath(os.getcwd())
settings_path = os.path.join(current_path,'Files','System','Settings.json')
settings = getSettings()


'''Folder Functions'''
def getFolderAnims(path: str):
    anim_indexes = []
    anim_count = 0
    
    for subdir,dirs,files in os.walk(path):
        for name in dirs:
        
            anim_indexes.append(['Anim '+str(anim_count),name,name,'Character','','False'])
            anim_count += 1
        
    return anim_indexes

'''MUGEN Functions'''

'''Reading Animation Data'''
def writeNull(anim_indexes: list, null_index_name: int, l: int, anim_count: int):
    anim_indexes.append(['Anim '+str(anim_count),'no name '+str(null_index_name),l,'Character','','False'])
    null_index_name += 1
    anim_count += 1
    return anim_indexes, null_index_name, anim_count


'''Get Animation Data MUGEN'''
def getAnimations(air_path: str):

    lines = readFile(air_path)

    anim_names = []
    anim_indexes = []
    null_index_name = 0
    anim_count = 0

    l = 0
    while l < len(lines):
        if '[Begin Action' in lines[l]:
            if lines[l+1] != '\n' or lines[l+1] != '' or lines[l+1] != ' \n':
            ##print(lines[l-1])
                if ';' in lines[l-1]:
                    if lines[l-1] != ';':
                        ##print(lines[l-1])
                        anim_name = lines[l-1].split(';')[1].strip()

                        if anim_name not in anim_names:
                            anim_indexes.append(['Anim '+str(anim_count),anim_name,l,'Character','','False'])
                            anim_names.append(anim_name)
                            anim_count += 1
                        else:
                            anim_indexes, null_index_name, anim_count = writeNull(anim_indexes, null_index_name, l, anim_count)
                    else:
                        anim_indexes, null_index_name, anim_count = writeNull(anim_indexes, null_index_name, l, anim_count)
                else:
                    anim_indexes, null_index_name, anim_count = writeNull(anim_indexes, null_index_name, l, anim_count)
        l += 1
    
    return anim_indexes, lines

'''Gets a count of the layers present'''
def getLayerCount(line: str, layers: int):
    
    temp_num = int(line.split(':')[1])
    if temp_num > layers:
        layers = temp_num

    return layers

'''Get Hurt/Hitbox data'''
def getBoxData(line: str,temp_data: list,layers: int,temp_data2: list,new_frameset: bool):
    if len(temp_data) == layers:
        temp_data = []
        if new_frameset == True:
            temp_data2 = []
            new_frameset = False
     
    values = line.split('=')[1]
    values = [int(v) for v in values.split(',')]
    temp_data.append(values)

    return temp_data,temp_data2,new_frameset

'''Get Animation Data'''
def getAnimData(anim_indexes: list, lines: list, sprite_names: list, hurt_check: bool, hit_check: bool):
    anim_data = {}

    a = 0
    while a < len(anim_indexes):
        combines = len(anim_indexes[a][0].split(','))
        c = 0
        new_dict = {'frame_data':[],
                    'sprite_names':[],
                    'sprite_pos':[],
                    'hurtbox_data':[],
                    'hitbox_data':[],
                    'type':[],
                    'invert':'',
                    'group':[]}
        
        while c < combines:
            start = int(str(anim_indexes[a][2]).split(',')[c])
            
            hitbox_layers = 0
            hurtbox_layers = 0
           
            i = start
            while i < len(lines):
                if 'Clsn1:' in lines[i]:
                    if hit_check != False:
                        hitbox_layers = getLayerCount(lines[i],hitbox_layers)
                elif 'Clsn2:' in lines[i] or 'Clsn2Default:' in lines[i]:
                    if hurt_check != False:
                        hurtbox_layers = getLayerCount(lines[i],hurtbox_layers)
                elif lines[i] == '\n':
                    end = i
                    break
                
                i += 1
                    
            temp_hurtbox_data = []
            temp_hitbox_data = []
            
            new_frameset = False
            hurt_frames = 0
            hit_frames = 0
            for line in range(start,end):

                if 'Clsn2:' in lines[line]:
                    hurt_frames = int(lines[line].replace('Clsn2:','').strip())
                elif 'Clsn2Default:' in lines[line]:
                    hurt_frames = int(lines[line].replace('Clsn2Default:','').strip())
                elif 'Clsn1:' in lines[line]:
                    hit_frames = int(lines[line].replace('Clsn1:','').strip())

                ## Hitbox
                elif (('Clsn1' in lines[line]) and ':' not in lines[line]) or (('Clsn2' in lines[line] or 'Clsn2Default' in lines[line]) and ':' not in lines[line]):
                    if hit_check != False:
                        if hit_frames > 0:
                            temp_hitbox_data,temp_hurtbox_data,new_frameset = getBoxData(lines[line],temp_hitbox_data,hitbox_layers,temp_hurtbox_data,new_frameset)
                            hit_frames -= 1

                    if hurt_check != False:
                        if hurt_frames > 0:
                            temp_hurtbox_data,temp_hitbox_data,new_frameset = getBoxData(lines[line],temp_hurtbox_data,hurtbox_layers,temp_hitbox_data,new_frameset)
                            hurt_frames -= 1
                
                ## Image data
                elif lines[line].count(',') >= 4:
                    new_frameset = True
                    data = lines[line].split(',')
                    if str(data[0]) != '-1':
                        sprite_number = str(data[0]).strip()+'-'+str(data[1]).strip()+'.png.meta'
                        sprite_check = False
                        for sprite_name in sprite_names:
                            i = 0
                            num_check = False
                            for s in sprite_name:
                                if s.isdigit() == True:
                                    num_check = True
                                    break
                                else:
                                    i += 1
                            if num_check == True:
                                new_name = sprite_name[i:]
                                #print(new_name)
                                if sprite_number == new_name:
                                    
                                    new_dict['sprite_names'].append(sprite_name)
                                    sprite_check = True

                        if sprite_check == False:
                            new_dict['sprite_names'].append(None)
                                
                    else:
                        new_dict['sprite_names'].append(None)
                    if anim_indexes[a][5] == 'True':
                        new_dict['sprite_pos'].append({'X':-1*(int(data[2].strip())),'Y':int(data[3].strip())})
                    else:
                        new_dict['sprite_pos'].append({'X':int(data[2].strip()),'Y':int(data[3].strip())})
                    frame_data = data[4].strip()
                    if ',' in frame_data:
                        new_dict['frame_data'].append(int(frame_data.split(',')[0].strip()))
                    else:
                        new_dict['frame_data'].append(int(frame_data))

                    blank_hurt = hurtbox_layers - len(temp_hurtbox_data)
                    if blank_hurt != 0:
                        for x in range(0,blank_hurt):
                            temp_hurtbox_data.append(None)

                    blank_hit = hitbox_layers - len(temp_hitbox_data)
                    if blank_hit != 0:
                        for x in range(0,blank_hit):
                            temp_hitbox_data.append(None)

                    
                    new_dict['hurtbox_data'].append(temp_hurtbox_data)
                    new_dict['hitbox_data'].append(temp_hitbox_data)

            c += 1
            
        new_dict['invert']= anim_indexes[a][5]
        new_dict['type'].append(anim_indexes[a][3])
        new_dict['type'].append(anim_indexes[a][4])
        anim_data[anim_indexes[a][1]] = new_dict
        a += 1
    #print(anim_data['Stand'])
    #exit()
    return anim_data


def getAxis(lines:list):
    for l in lines:
        if 'X axis:' in l:
            x = l.split(':')[1].strip()        
            image_align_x = -1*int(x)
        elif 'Y axis:' in l:
            y = l.split(':')[1].strip()
            image_align_y = -1*int(y)
            
    return image_align_x, image_align_y

'''Get Sprite Related Data'''
def getSpriteData(path: str):
    sprite_data = {}
    sprite_names = []
    #char_name = ''
    image_align_x, image_align_y = 0,0
    
    for f in os.listdir(path):
        if '.meta' in f and '.txt' not in f:
            data = getJSONData(path+'\\'+f)
            sprite_data[f] = data['guid']
            sprite_names.append(f)
            #if char_name == '':
            #    char_name = f.split('_')[0]+'_'
                
        elif '.txt' in f and '.meta' not in f:
            lines = readFile(path+'\\'+f)
                
            image_align_x, image_align_y = getAxis(lines)
                                
    return sprite_data, sprite_data.keys(), image_align_x, image_align_y, sprite_names


def getSpritePos(path:str):
    sprite_pos = []
    for f in os.listdir(path):
        if '.png' in f and '.meta' not in f:
            im = Image.open(os.path.join(path,f))
            width,height = im.size
            sprite_pos.append({'X':(width/2)*-1,'Y':height*-1})
            
    return sprite_pos

def getSpritePosList(path:str, names:list):
    sprite_pos = []
    for n in names:
        if n != 'None':
            im = Image.open(os.path.join(path,n))
            width,height = im.size
            sprite_pos.append({'X':(width/2)*-1,'Y':height*-1})
        else:
            sprite_pos.append({'X':0,'Y':0})
            
    return sprite_pos

def readFFE(path:str, groups:list):
    data = readFile(path)
    ffe_data = {}
    sprite_check = False
    d = 0
    invalid_names = {}
    while d < len(data):
        
        if '[SpriteDef]' in data[d]:
            sprite_name = data[d+7].split('= ')[1].strip()
            group = int(data[d+1].split('=')[1].strip())
            image = int(data[d+2].split('=')[1].strip())
            xaxis = int(data[d+3].split('=')[1]) * -1
            yaxis = int(data[d+4].split('=')[1]) * -1
            group_check = False
            for g in groups:
                if g == group:
                    group_check = True

            if group_check == True:
                ffe_data[sprite_name] = {'X':xaxis,'Y':yaxis}

            if str(group)+'-'+str(image)+'.png' != sprite_name:
                invalid_names[str(group)+'-'+str(image)+'.png.meta'] = sprite_name+'.meta'

            
            d += 8
        else:
            d += 1
        
    return ffe_data, invalid_names


def getSpritePosFFE(names:list, ffe_data:dict):
    sprite_pos = []
    for n in names:
        if n != 'None':
            sprite_pos.append(ffe_data[n])
        else:
            sprite_pos.append({'X':0,'Y':0})

    return sprite_pos

def makeSymbol(alpha,color,pivots,rotation,user_scale,obj_scale,obj_type,pos):
    guid = str(uuid.uuid4())
    new_symbol = {"$id":guid,
                  "alpha": alpha,
                  "color": color,
                  "pivotX": pivots[0],
                  "pivotY": pivots[1],
                  "pluginMetadata": {
                  },
                  "rotation": rotation,
                  "scaleX": user_scale[0] * obj_scale[0],
                  "scaleY": user_scale[1] * obj_scale[1],
                  "type": obj_type,
                  "x": pos[0] * user_scale[0],
                  "y": pos[1] * user_scale[1]
                  }
    return guid, new_symbol


def makeKeyframe(f: int,symbol: str, key_type: str):
    new_guid = str(uuid.uuid4())
    new_keyframe = {"$id":new_guid,
                    "length":int(f),
                    "pluginMetadata": {
                    },
                    "symbol": symbol,
                    "tweenType":"LINEAR",
                    "tweened":False,
                    "type":key_type
                    }
    return new_guid, new_keyframe


def makeHKeyframes(h_data: list, scale_x: float, scale_y: float, h_keyframes: dict,f: int, ce_data: dict, invert: str):
    hl = 0
    for h in h_data:        
        if h == None:
            #img_h_guid = str(uuid.uuid4())

            img_h_guid, new_keyframe = makeKeyframe(f,None,"COLLISION_BOX")
            
            ce_data["keyframes"].append(new_keyframe)
            h_keyframes[hl].append(img_h_guid)
        else:     
            guid = str(uuid.uuid4())
            
            #if invert == 'True':
            #    print(h[0])
            #    print(h[2])
        
            scaleX = (h[0] - h[2])
            scaleY = (h[1] - h[3])
            if scaleX > 0:
                if invert ==  'True':
                    x = (-1*scaleX)+(-1*h[2])
                    #print(x)
                    #print('get here')
                else:
                    x = h[2]
            else:
                if invert == 'True':
                    x = h[2] * -1
                    scaleX *= -1
                else:
                    
                    x = h[0]
                    scaleX *= -1

            if scaleY > 0:
                y = h[3]
            else:
                y = h[1]
                scaleY *= -1
                        

            guid, new_symbol_h = makeSymbol(None,None,[0,0],0,[scale_x,scale_y],[scaleX,scaleY],"COLLISION_BOX",[x,y])
                            
            ce_data["symbols"].append(new_symbol_h)

            img_h_guid, new_keyframe = makeKeyframe(f,guid,"COLLISION_BOX")
                            
            ce_data["keyframes"].append(new_keyframe)
            h_keyframes[hl].append(img_h_guid)

        hl += 1

    return h_keyframes, ce_data

def makeHLayers(h_keyframes,h_type,h_name,color,layers,ce_data):
    h_count = 0
    for h in h_keyframes:
        img_h_guid = str(uuid.uuid4())
        new_h_layer = {"$id":img_h_guid,
                       "defaultAlpha": 0.5,
                       "defaultColor": color,
                       "hidden": False,
                       "keyframes": h,
                       "locked": False,
                       "name": h_name+str(h_count),
                       "pluginMetadata": {
                            "com.fraymakers.FraymakersMetadata": {
                            "collisionBoxType": h_type,
                                "index": h_count
                            }
                        },
                       "type": "COLLISION_BOX"
                       }
        
        ce_data["layers"].append(new_h_layer)
        layers.append(img_h_guid)
        h_count += 1

    return layers, ce_data


def editCE(ce_data,anim_data,sprite_data,sprite_data_keys,scale_x,scale_y,image_align_x,image_align_y, projectile_data):
    og_scale_x = scale_x
    #og_image_algin_x = image_align_x
    
    for k,v in anim_data.items():

        img_keyframes = []

        if v['type'][0] == 'Projectile':
            i = 0
            while i < len(projectile_data):
                if projectile_data[i]['id'] == v['type'][1]:
                    p = projectile_data[i]
                    p_index = i
                    break
                i += 1   
        
        
        if v['hitbox_data'] != []:
            hit_layers = max(len(item) for item in v['hitbox_data'])
            hit_keyframes = [[] for h in range(0,hit_layers)]

        if v['hitbox_data'] != []:
            hurt_layers = max(len(item) for item in v['hurtbox_data'])
            hurt_keyframes = [[] for h in range(0,hurt_layers)]

        if v['invert'] == 'True':
            if scale_x == og_scale_x:
                scale_x *= -1
        else:
            if scale_x != og_scale_x:
                scale_x *= -1
        
        
        for f,sn,hurt,hit,pos in zip(v['frame_data'],v['sprite_names'],v['hurtbox_data'],v['hitbox_data'],v['sprite_pos']):
            if int(f) == -1:
                f = 1
                
            imageAsset = None
            if sn != None:
                for sdk in sprite_data_keys:
                    if sn == sdk:
                        imageAsset = sprite_data[sdk]
                       
                img_guid = str(uuid.uuid4())
                new_symbol = {"$id":img_guid,
                              "alpha":1,
                              "imageAsset":imageAsset,
                              "pivotX":400,
                              "pivotY":400,
                              "pluginMetadata":{
                              },
                              "rotation":0,
                              "scaleX":scale_x,
                              "scaleY":scale_y,
                              "type":"IMAGE",
                              "x":(image_align_x + pos['X']) * scale_x,
                              "y":(image_align_y +pos['Y']) * scale_y
                              }
            
                

                if v['type'][0] == 'Character' or v['type'][0] == 'Vfx':
                    ce_data["symbols"].append(new_symbol)
                else:
                    p["symbols"].append(new_symbol)

                img_k_guid, new_keyframe = makeKeyframe(f,img_guid,"IMAGE")

            else:
                img_k_guid, new_keyframe = makeKeyframe(f, None,"IMAGE")

            if v['type'][0] == 'Character' or v['type'][0] == 'Vfx':
                ce_data["keyframes"].append(new_keyframe)
            else:
                p["keyframes"].append(new_keyframe)

            img_keyframes.append(img_k_guid)
            
            if hurt_layers != 0:
                if v['type'][0] == 'Character' or v['type'][0] == 'Vfx':
                    hurt_keyframes,ce_data = makeHKeyframes(hurt, og_scale_x, scale_y, hurt_keyframes,f,ce_data,v['invert'])
                else:
                    hurt_keyframes,p = makeHKeyframes(hurt, og_scale_x, scale_y, hurt_keyframes,f,p,v['invert'])

            else:
                hurt_keyframes = []
                
            if hit_layers != 0:

                if v['type'][0] == 'Character' or v['type'][0] == 'Vfx':
                    hit_keyframes,ce_data = makeHKeyframes(hit, og_scale_x, scale_y, hit_keyframes,f,ce_data,v['invert'])
                else:
                    hit_keyframes,p = makeHKeyframes(hit, og_scale_x, scale_y, hit_keyframes,f,p,v['invert'])
            else:
                hit_keyframes = []
                

        layers = []        
        img_l_guid = str(uuid.uuid4())
        new_layer = {"$id":img_l_guid,
                     "hidden":False,
                     "keyframes":img_keyframes,
                     "locked":False,
                     "name":"Image Layer",
                     "pluginMetadata":{},
                     "type":"IMAGE"
                    }

        #print(new_layer)
        if v['type'][0] == 'Character' or v['type'][0] == 'Vfx':
            ce_data["layers"].append(new_layer)
        else:
            p["layers"].append(new_layer)
        
        layers.append(img_l_guid)

        #print(hit_keyframes)
        if v['type'][0] == 'Character' or v['type'][0] == 'Vfx':
            layers, ce_data = makeHLayers(hit_keyframes,"HIT_BOX","hitbox","0xff0000",layers,ce_data)
        else:
            layers, p = makeHLayers(hit_keyframes,"HIT_BOX","hitbox","0xff0000",layers,p)

        if v['type'][0] == 'Character' or v['type'][0] == 'Vfx':
            layers, ce_data = makeHLayers(hurt_keyframes,"HURT_BOX","hurtbox","0xf5e042",layers,ce_data)
        else:
            layers, p = makeHLayers(hurt_keyframes,"HURT_BOX","hurtbox","0xf5e042",layers,p)
        

        if v['type'][0] != 'Vfx':
            anim_guid = str(uuid.uuid4())
            new_animation = {"$id":anim_guid,
                             "layers":layers,
                             "name":k,
                             "pluginMetadata":{}
                             }

            
            if v['type'][0] == 'Character':
                ce_data["animations"].append(new_animation)
                
            elif v['type'][0] == 'Projectile':
                p["animations"].append(new_animation)
                projectile_data[p_index] = p
        else:
            anims = ce_data['animations']
            a = 0
            while a < len(anims):
                if anims[a]['name'] == v['type'][1]:
                    ce_data['animations'][a]['layers'].insert(1,img_l_guid)
                a += 1
            
    return ce_data, projectile_data

'''New Project Functions'''
def moveTemplate(template_path,project_path,sprite_path):
    list_dir = os.listdir(template_path)

    shutil.copytree(template_path,project_path,dirs_exist_ok=True)
    #shutil.copytree(sprite_path,os.path.join(project_path,'library','sprites'),dirs_exist_ok=True)

def moveSprites(project_path,sprite_path):
    for f in os.listdir(sprite_path):
        if '.png' in f:
            shutil.copyfile(os.path.join(sprite_path,f),os.path.join(project_path,f))

def trim(im,f):
    im2 = im.getcolors()
    
    if len(im2) > 1:
        bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
        diff = ImageChops.difference(im, bg)
        #diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        if bbox:
            return im.crop(bbox)
        else: 
            # Failed to find the borders, convert to "RGB"        
            return trim(im.convert('RGB'),f)
    else:
        return False

def trimSprites(path:str):
    for f in os.listdir(path):
        if '.png' in f and '.meta' not in f:
            im = Image.open(os.path.join(path,f))
            new_im = trim(im,f)
            if new_im == False:
                img = Image.new('RGBA',(1,1),color = (255,255,255,0))
                img.save(os.path.join(path,f))
            else:
                new_im.save(os.path.join(path,f))
    
    

def newImageSymbols(path:str):
    for subdir, dirs, files in os.walk(folder_path):
        for file in files:
            if file+'.meta' not in files and '.meta' not in file and '.txt' not in file:
                
                new_symbol = makeImageSymbol()
                #print(os.path.join(path,subdir,file+'.meta'))
                writeNewCE(new_symbol,os.path.join(path,subdir,file+'.meta'))


def makeImageSymbol():
    new_symbol = {"export":False,
                  "guid":str(uuid.uuid4()),
                  "id":"",
                  "pluginMetadata":{},
                  "plugins":[],
                  "tags":[],
                  "version":2
                  }
    return new_symbol
    
    

def createEntity(name, object_type):
    entity_guid = str(uuid.uuid4())
    new_entity = {'animations':[],
                  'export':True,
                  'guid':entity_guid,
                  'id':name,
                  'keyframes':[],
                  'layers':[],
                  'paletteMap':{
                      'paletteCollection':None,
                      'paletteMap':None
                  },
                  "pluginMetadata": {
                      "com.fraymakers.FraymakersMetadata": {
                          "objectType": object_type,
                          "version": "0.1.1"
                      }
                  },
                  'plugins':["com.fraymakers.FraymakersMetadata"],
                  'symbols':[],
                  'tags':[],
                  'terrains':[],
                  'tilesets':[],
                  'version':14
                  }

    return new_entity
                  

def getManifest(path):
    data = open(path)
    data = json.load(data)
    return data


def addProjectileManifest(manifest,name):
    new_projectile = {'id':name,
                      'type':'projectile',
                      'objectStatsId':name+'ProjStats',
                      'animationStatsId':name+'AnimStats',
                      'hitboxStatsId':name+'HitboxStats',
                      'scriptId':name+'Script',
                      'costumesId':name+'Costumes'}
    
    manifest['content'].append(new_projectile)
    return manifest

def getProjectileContent(file_name):
    with open('Files\\Projectile\\'+file_name+'.hx', 'r') as file:
        content = file.readlines()
    return content

def createProjectile(name, project_path):
    if os.path.exists(project_path+'\\library\\scripts\\'+name) == False:
        os.makedirs(project_path+'\\library\\scripts\\'+name)
        manifest = getManifest(project_path+'\\library\\manifest.json')
        manifest = addProjectileManifest(manifest,name)
        writeNewCE(manifest,project_path+'\\library\\manifest.json')
        file_names = ['AnimationStats','HitboxStats','Script','Stats']
        file_guids = []
        for f in file_names:
            f_content = getProjectileContent(f)
            with open(project_path+'\\library\\scripts\\'+name+'\\'+name+f+'.hx','w') as file:
                file.writelines(f_content)

            new_guid = str(uuid.uuid4())
            file_guids = new_guid
            if f != 'Script':
                metadata = {'export':True,
                            'guid':new_guid,
                            'id':name+f,
                            'language':'hscript',
                            'pluginMetadata':{},
                            'plugins':[],
                            'tags':[],
                            'version':1
                            }
            else:
                metadata = {'export':True,
                            'guid':new_guid,
                            'id':name+f,
                            'language':'hscript',
                            'pluginMetadata':{
                                'com.fraymakers.FraymakersMetadata':{
                                    'objectType':'PROJECTILE',
                                    'version':'0.1.1'
                                }
                            },
                            
                            'plugins':['com.fraymakers.FraymakersMetadata'],
                            'tags':[],
                            'version':1
                            }

            with open(project_path+'\\library\\scripts\\'+name+'\\'+name+f+'.hx.meta','w') as file:
                json.dump(metadata, file, ensure_ascii=False, indent=4)
                
        new_entity = createEntity(name, 'PROJECTILE')
        print(new_entity)

        #with open(project_path+'\\library\\entities\\'+name, 'w') as file:
            #json.dump(new_entity, file, ensure_ascii=False, indent=4)


    return new_entity


'''Palette Functions'''
def decodePalette(palette_path):
    with open(palette_path, 'rb') as act:
        raw_data = act.read()                           # Read binary data
    hex_data = encode(raw_data, 'hex')
    
    colors = []
    hd = 0
    while hd < len(hex_data):
        colors.append(hex_data[hd:hd+6].decode())
        hd += 6
        
    colors = ['0xFF'+i for i in colors if len(i)]
    colors = [c for c in colors if c != '0xFF000000']
    ##return colors, total_colors_count
    return colors

def importPalette(base_palette,palette_files,costume_palette):
    base_colors = list(reversed(decodePalette(base_palette)))
    #print(base_colors)
    #exit()
    costume_data = getJSONData(costume_palette)
    costume_data['colors'] = []
    colors = costume_data['colors']
    costume_data['maps'] = []
    maps = costume_data['maps']
    color_count = 0
    color_guids = []
    map_guid = str(uuid.uuid4())
    base_map = {"$id":map_guid,
                "colors":[],
                "name":"Base",
                "pluginMetadata": {
                    "com.fraymakers.FraymakersMetadata": {
                        "isBase":True
                        }
                    }
                }
    for bc in base_colors:
        guid = str(uuid.uuid4())
        new_color = {"$id":guid,
                     "color":bc,
                     "name":"Color"+str(color_count),
                     "pluginMetadata":{}
                     }

        colors.append(new_color)
        color_guids.append(guid)
        color_count += 1

        base_map['colors'].append({"paletteColorId":guid,
                                   "targetColor":bc})

    costume_data['colors'] = colors
    maps.append(base_map)

    palette_files = palette_files.split(';')
    for p in palette_files:
        name = p.split('/')
        name = name[-1]
        name = name.split('.act')[0]
        map_colors = list(reversed(decodePalette(p)))
        map_guid = str(uuid.uuid4())
        new_map = {"$id":map_guid,
                   "colors":[],
                   "name":name,
                   "pluginMetadata":{
                       "com.fraymakers.FraymakersMetadata": {
                           "isBase":False
                           }
                       }
                   }

        for cg,mc in zip(color_guids,map_colors):
            new_map['colors'].append({'paletteColorId':cg,
                                      'targetColor':mc})

        maps.append(new_map)
        
    costume_data['maps'] = maps

    writeNewCE(costume_data,costume_palette)


'''Creates the Fray Theme'''
fray_theme = {'BACKGROUND': '#323232',
             'TEXT': '#e2eef5',
             'INPUT': '#585858',
             'TEXT_INPUT': '#cecad0',
             'SCROLL': '#585858',
             'BUTTON': ('#e2eef5', '#585858'),
             'PROGRESS': ('#f5ba04', '#6b6b6b'),
             'BORDER': 1,
             'SLIDER_DEPTH': 0,
             'PROGRESS_DEPTH': 0}

sg.theme_add_new('fraymakers', fray_theme)                   

sg.theme('fraymakers')
sg.set_options(font=('Calibri',12))

'''Window Functions'''
def update_visibility(elements: dict):
    '''
    Updates the visibility
    of specified elements
    '''
    global window
    for k,v in elements.items():
        window[k].update(visible=v)

def update_table_values(table_name: str):
    '''
    Updates table values
    based upon table name
    '''
    global window
    
    window['db_table'].update(values=anim_indexes)
    
    return anim_indexes

def update_disabled(elements: dict):
    '''
    Updates the disabled
    status of buttons
    '''
    global window
    for k,v in elements.items():
        window[k].update(disabled=v)

def update_name_tracker(user_names: list):
    '''
    Updates the name tracker
    table
    '''

    used_names = []
    for ai in anim_indexes:
        if ai[1] in default_names:
            used_names.append(ai[1])
            
    for dn in default_names:
        if dn in used_names:
            window[dn].update(background_color = '#00e673')
        else:
            window[dn].update(background_color = '#ff6666')

def update_table(anim_indexes: list, selected_index):
    if type(selected_index) == int:
        if selected_index == -1:
            window['anim_table'].update(values=anim_indexes)
        else:
            selected_index = [selected_index]
            window['anim_table'].update(values=anim_indexes,select_rows=selected_index)
    else:
        window['anim_table'].update(values=anim_indexes,select_rows=selected_index)
        
    writeAnimIndexes(anim_indexes,os.path.join('Files','System','Backup Anims.json'))

def update_filebrowse(settings: dict):
    mugen_keys = ['Base Palette Browse','Palette Files Browse','sprite_folder_browse','air_browse','mugen_folder']
    fraymakers_keys = ['Costumes File Browse','ce_filebrowse','sprite_folder_browse','project_folder_browse','folder_frame_sprite','fraymakers_folder','folder_import']
    for m in mugen_keys:
        window[m].InitialFolder = settings['Mugen Folder']

    for f in fraymakers_keys:
        window[f].InitialFolder = settings['Fraymakers Folder']

'''Layouts'''
def makeAnimRenamer(anim_indexes,header):

    type_frame = [[sg.Button('Character',key='type_Character',disabled=True),
                   sg.Button('Projectile',key='type_Projectile',disabled=True),
                   sg.Button('VFX',key='type_Vfx',disabled=True)],
                  [sg.Text('Edit Type Data'),sg.Input(size=25,key='new_type_data'),sg.Button('Edit Type Data',key='edit_type_data',disabled=True)]]

    json_import_frame = [[sg.Text('Import from JSON File',font=('Edit Undo BRK',18)),
                          sg.InputText(key='json_import_path',size=25),
                          sg.FileBrowse(initial_folder = os.path.join(cwd,'Files','System'),file_types=(('JSON','*.json'),)),
                          sg.Button('Import',key='get_json_names')],
                          [sg.Text('Save Name',font=('Edit Undo BRK',18)),
                           sg.InputText(key='json_save_name',size=25)],
                          [sg.Text('Save Folder',font=('Edit Undo BRK',18)),
                           sg.InputText(key='json_save_path',size=25),
                           sg.FolderBrowse(),
                           sg.Button('Save',key='json_save_file')]]
                           

    anim_layout = [[sg.Table(anim_indexes,key='anim_table',
                             headings=header,
                             enable_events=True,display_row_numbers=True)],
                   [sg.Button('Delete Row(s)',key='delete_row',disabled=True),
                    sg.Button('Copy Row(s)',key='copy_row', disabled=True),
                    sg.Button('▲',key='move_up',disabled=True),
                    sg.Button('▼',key='move_down',disabled=True),
                    sg.Button('Combine',key='combine',disabled=True),
                    sg.Button('Invert',key='invert',disabled=True)],
                   [sg.Text('Edit Anim Name'),sg.Input(size=25,key='new_name'),sg.Button('Edit Row',key='edit_name',disabled=True)],
                   [sg.Frame('Edit Type(s)',type_frame,element_justification='c')],
                   [sg.Frame('Save/Load Names',json_import_frame,element_justification='l')],
                   #[sg.Button('Sort Names',key='sort_names')],
                   [sg.Button('Submit',key='submit anims')]]

    return anim_layout


anim_layout = [[]]

name_table_layout = []

i = 0
while i < len(default_names):
    temp_layout = []
    for x in range(0,6):
        if i+x < len(default_names):
            temp_layout.append(sg.Text(default_names[i+x], key=default_names[i+x], size=(18,1), background_color='#ff6666',border_width=2))
        else:
            temp_layout.append(sg.Text('', key=str(i+x), size=(18,1)))
        
    name_table_layout.append(temp_layout)
    i += 6

name_tracker_layout = [[sg.Button('>',key='Show Name Tracker'),
                        sg.Button('<',key='Hide Name Tracker', visible=False),
                        sg.Column(name_table_layout,key='Name Table Layout',element_justification='c',visible=False)]]
                    
anim_name_layout = [[sg.Column(anim_layout, key='Anim Layout', element_justification='c'),
                     sg.Column(name_tracker_layout, key='Name Tracker Layout', element_justification='c')]]

palette_frame = [[sg.Text('Base Palette',font=('Edit Undo BRK',18)),sg.InputText(key='Base Palette Path',size=25),sg.FileBrowse(key='Base Palette Browse',initial_folder=settings['Mugen Folder'],file_types=(('Act Files','*.act'),))],
                 [sg.Text('Palette Files',font=('Edit Undo BRK',18)),sg.InputText(key='Palette Files Path',size=25),sg.FilesBrowse(key='Palette Files Browse',initial_folder=settings['Mugen Folder'],file_types=(('Act Files','*.act'),))],
                 [sg.Text('Costumes File',font=('Edit Undo BRK',18)),sg.InputText(key='Costumes File Path',size=25),sg.FileBrowse(key='Costumes File Browse',initial_folder=settings['Fraymakers Folder'],file_types=(('Palette Files','*.palettes'),))]]

ce_entity =[[sg.Text('Character Entity File',font=('Edit Undo BRK',18)),sg.InputText(key='Character Entity Path',size=25),sg.FileBrowse(key='ce_filebrowse',initial_folder=settings['Fraymakers Folder'],
                                                                                                                                        file_types=(('Entity Files','*.entity'),))]]

ce_template = [[sg.Text('Template',font=('Edit Undo BRK',18)),sg.InputText(key='Mugen Template',size=25),sg.FolderBrowse(initial_folder=os.path.expandvars(R"C:\Users\$USERNAME\FrayToolsData\templates"))]]


ce_layout = [[sg.Text('Scale-X'),sg.Input(default_text='1',key='Scale-X',size=5),
              sg.Text('Scale-Y'),sg.Input(default_text='1',key='Scale-Y',size=5)],
             [sg.Column(ce_entity,key='CE Entity Layout',element_justification='c'),
              sg.Column(ce_template,key='CE Template Layout',element_justification='c', visible=False)],
             [sg.Text('Sprite Folder',font=('Edit Undo BRK',18)),sg.InputText(key='Sprite Folder Path',size=25),sg.FolderBrowse(key='sprite_folder_browse',initial_folder=settings['Fraymakers Folder'])],
             [sg.Text('Project Folder',font=('Edit Undo BRK',18)),sg.InputText(key='Project Folder Path',size=25),sg.FolderBrowse(key='project_folder_browse',initial_folder=settings['Fraymakers Folder'])],
             [sg.Checkbox('Hitboxes',default=True,key='Hitboxes Check'),sg.Checkbox('Hurtboxes',default=True,key='Hurtboxes Check')],
             [sg.Checkbox('Import Palettes',default=True,key='Import Palettes',enable_events=True)],
             [sg.Checkbox('Sprites Not-Aligned',default=True,key='unaligned_check',enable_events=True)],
             [sg.Text('FFE File Path',font=('Edit Undo BRK',18)),sg.InputText(key='ffe_file_path',size=25),sg.FileBrowse(key='ffe_file_browse',initial_folder=settings['Fraymakers Folder'],file_types=(('FFE Files','*.ffe'),))],
             #[sg.Checkbox('Trim Sprites',default=False,key='Trim Sprites'), sg.Checkbox('Only Include Animation Sprites',default=False,key='Animation Sprites')],
             [sg.Frame("Palette Frame",palette_frame,key='palette_frame')],
             [sg.Button('Submit',key='submit ce')]]



folder_ce_layout = [[sg.Text('Scale-X'),sg.Input(default_text='1',key='Scale-X Folder',size=5),
                     sg.Text('Scale-Y'),sg.Input(default_text='1',key='Scale-Y Folder',size=5)],
                    [sg.Checkbox('Auto-Align based on image',default=True,key='folder_align_check'),sg.Checkbox('Sprites in project folder',default=True,key='sprite_folder_check')],
                    [sg.Text('Character Entity File',font=('Edit Undo BRK',18)),sg.InputText(key='Character Entity Path Folder',size=25),sg.FileBrowse()],
                    [sg.Button('Submit',key='submit ce folder')]]

new_folder_ce_layout = [[sg.Text('Scale-X'),sg.Input(default_text='1',key='Scale-X Folder New',size=5),
                         sg.Text('Scale-Y'),sg.Input(default_text='1',key='Scale-Y Folder New',size=5)],
                        [sg.Checkbox('Auto-Align based on image',default=True,key='new_folder_align_check')],
                        [sg.Text('Template',font=('Edit Undo BRK',18)),sg.InputText(key='Folder Template',size=25),sg.FolderBrowse(initial_folder=os.path.expandvars(R"C:\Users\$USERNAME\FrayToolsData\templates"))],
                        [sg.Text('Project Folder',font=('Edit Undo BRK',18)),sg.InputText(key='Folder New',size=25),sg.FolderBrowse(key='folder_import',initial_folder=settings['Fraymakers Folder'])],
                        [sg.Button('Submit',key='submit new ce folder')]]

folder_frame = [[sg.Text('Sprite Folder',font=('Edit Undo BRK',18)),sg.InputText(key='Project Folder',size=25),sg.FolderBrowse(key='folder_frame_sprite',initial_folder=settings['Fraymakers Folder'])]]
mugen_frame = [[sg.Text('Mugen .air File',font=('Edit Undo BRK',18)),sg.InputText(key='AIR File',size=25),sg.FileBrowse(key='air_browse',initial_folder=settings['Mugen Folder'],
                                                                                                                        file_types=(('Air Files','*.air'),))]]
roa_frame = [[]]

start_layout = [[sg.Checkbox('Folder',default=True,key='folder_import',enable_events=True),
                 sg.Checkbox('Mugen',default=False,key='mugen_import',enable_events=True,disabled=True),
                 sg.Checkbox('ROA',default=False,key='roa_import',enable_events=True,disabled=True,visible=False)],
                [sg.Checkbox('New Project',default=False,key='new_project',enable_events=True),
                 sg.Checkbox('Palette Only',default=False,key='only_palette',enable_events=True,visible=False)],
                [sg.Frame('Folder Import',folder_frame,key='folder_frame'),
                 sg.Frame('Mugen Import',mugen_frame,key='mugen_frame',visible=False),
                 sg.Frame('ROA Import',roa_frame,key='roa_frame',visible=False)],
                [sg.Button('Settings',key='settings')],
                [sg.Button('Go',key='go'),sg.Button('Exit')]]

settings_layout =[[sg.Text('Mugen Folder',font=('Edit Undo BRK',18)),
                   sg.InputText(default_text=settings['Mugen Folder'],key='settings_mugen',size=25),
                   sg.FolderBrowse(key='mugen_folder',initial_folder=settings['Mugen Folder'])],
                  [sg.Text('Fraymakers Folder',font=('Edit Undo BRK',18)),
                   sg.InputText(default_text=settings['Fraymakers Folder'],key='settings_fraymakers',size=25),
                   sg.FolderBrowse(key='fraymakers_folder',initial_folder=settings['Fraymakers Folder'])],
                  [sg.Button('Save',key='settings_save'),sg.Button('Exit',key='settings_exit')]]


layout = [[sg.Text('Fraytools Anim Importer V.85', justification='center',font=('Centie Sans',26))],
          [sg.Column(start_layout, key='Start Layout', element_justification='c'),
           sg.Column(settings_layout, key='Settings Layout', element_justification='c', visible=False),
           sg.Column(anim_name_layout, key='Anim Name Layout', element_justification='c', visible=False),
           sg.Column(ce_layout, key='CE Layout', element_justification='c', visible=False),
           sg.Column(folder_ce_layout, key='Folder CE Layout', element_justification='c', visible=False),
           sg.Column(new_folder_ce_layout, key='Folder New CE Layout', element_justification='c', visible=False)]]
          

window = sg.Window('Fraytools Mugen Importer',layout,element_justification = 'center')

while True:
    event, values = window.read()
    
    if event == None or event == 'Exit':
        window.close()
        break

    elif event == 'go':
        if values['only_palette'] == True:
            update_visibility({'Start Layout': False,'CE Layout': True,'CE Entity Layout':False})
            update_disabled({'Scale-X':True,'Scale-Y':True,
                             'Sprite Folder Path':True,'Project Folder Path':True,
                             'sprite_folder_browse':True,'project_folder_browse':True,
                             'Hitboxes Check':True,'Hurtboxes Check':True,
                             'Import Palettes':True})
            
        elif values['mugen_import'] == True:
            if checkFile(values['AIR File']) == True:
                window['Start Layout'].update(visible=False)
                mugen_air = values['AIR File']
                anim_indexes, anim_lines = getAnimations(mugen_air)
                anim_layout= makeAnimRenamer(anim_indexes,['Animation Number','Animation Name','Line Start in File','Type','Type Data','Invert'])
                window.extend_layout(window['Anim Layout'],anim_layout)
                update_name_tracker(anim_indexes)
                if values['new_project'] == False:
                    sg.popup('Please backup your entire Character folder before proceeding!')
                window['Anim Name Layout'].update(visible = True)
            

        elif values['folder_import'] == True:
            if checkFolder(values['Project Folder']) == True:
                window['Start Layout'].update(visible=False)
                folder_path = values['Project Folder']
                anim_indexes = getFolderAnims(folder_path)
                anim_layout= makeAnimRenamer(anim_indexes,['Animation Number','Animation Name','OG Folder','Type','Type Data','Invert'])
                window.extend_layout(window['Anim Layout'],anim_layout)
                update_name_tracker(anim_indexes)
                if values['new_project'] == False:
                    sg.popup('Please backup your entire Character folder before proceeding!')
                window['Anim Name Layout'].update(visible = True)
        

    elif event == 'settings':
        update_visibility({'Start Layout':False,'Settings Layout':True})

    elif event == 'settings_save':
        
        settings = {'Mugen Folder':values['settings_mugen'],
                        'Fraymakers Folder':values['settings_fraymakers']}
        writeNewCE(settings,settings_path)
        update_filebrowse(settings)
        sg.popup('Settings Saved!')
        
                                                                    

    elif event == 'settings_exit':
        update_visibility({'Start Layout':True,'Settings Layout':False})

    elif 'import' in event:
        if values['folder_import'] == True:
            update_visibility({'folder_frame':True})
            update_disabled({'mugen_import':True,'roa_import':True,'go':False})
        elif values['mugen_import'] == True:
            update_visibility({'mugen_frame':True,'only_palette':True})
            #window['mugen_frame'].update(visible=True)
            update_disabled({'folder_import':True,'roa_import':True,'go':False})
        elif values['roa_import'] == True:
            window['roa_frame'].update(visible=True)
            update_disabled({'folder_import':True,'mugen_import':True,'go':False})
        else:
            hide_frame = event.split('_')[0]
            window[hide_frame+'_frame'].update(visible=False)
            update_visibility({'only_palette':False})
            update_disabled({'folder_import':False,'mugen_import':False,'roa_import':False,'go':True})

    elif event == 'only_palette':
        if values['only_palette'] == True:
            update_disabled({'AIR File': True,'air_browse':True})
        else:
            update_disabled({'AIR File': False,'air_browse':False})

    elif event == 'anim_table':
        
        selected_index = values[event]
        selected_row = [anim_indexes[row] for row in values[event]]
        #print(selected_index)
        #print(selected_row)
        
        if len(selected_index) != 0 :
            if len(selected_index) > 1:
                update_disabled({'delete_row':False,'copy_row':False,'edit_name':True,'move_up':True,'move_down':True,'combine':False,'invert':False,
                                 'type_Character':False,'type_Projectile':False,'type_Vfx':False,'edit_type_data':False,})
            else:
                selected_index = selected_index[0]
                if selected_index == 0:
                    update_disabled({'move_up':True,'move_down':False})
                elif selected_index == len(anim_indexes):
                    update_disabled({'move_up':False,'move_down':True})
                else:
                    update_disabled({'move_up':False,'move_down':False})
                    
                update_disabled({'delete_row':False,'copy_row':False,'edit_name':False,'combine':True,'invert':False,
                                 'type_Character':False,'type_Projectile':False,'type_Vfx':False,'edit_type_data':False})
        else:
            update_disabled({'delete_row':True,'copy_row':True,'edit_name':True,'move_up':True,'move_down':True,'combine':True,'invert':True,
                                 'type_Character':True,'type_Projectile':True,'type_Vfx':True,'edit_type_data':True})

    elif event == 'edit_name':
        new_name = values.get('new_name')
        #print(new_name)

        anim_indexes[selected_index][1] = new_name
        update_name_tracker(anim_indexes)
        update_table(anim_indexes,selected_index)

    elif event == 'copy_row':
        animation_number = selected_row[0][0]
        anim_nums = [x[0] for x in anim_indexes]
        
        new_data = [animation_number+' (copy)',selected_row[0][1],selected_row[0][2],selected_row[0][3],selected_row[0][4],selected_row[0][5]]
        
        anim_indexes.insert(selected_index, new_data)
        update_table(anim_indexes,selected_index)

    elif event == 'delete_row':
        anim_indexes.pop(selected_index)
        if selected_index == len(anim_indexes):
            update_table(anim_indexes,selected_index - 1)
        else:
            update_table(anim_indexes,selected_index)

    elif event == 'move_up':
        anim_indexes.insert(selected_index-1, selected_row[0])
        anim_indexes.pop(selected_index+1)
        selected_index -= 1
        update_table(anim_indexes,selected_index)
        
    elif event == 'move_down':
        anim_indexes.insert(selected_index+2, selected_row[0])
        anim_indexes.pop(selected_index)
        selected_index += 1
        update_table(anim_indexes,selected_index)

    elif 'type' in event and 'edit' not in event:
        type_change = event.split('_')[1]
        print(type_change)
        print(selected_index)

        if type(selected_index) == list:
            s = 0
            while s < len(list(selected_index)):
                anim_indexes[selected_index[s]][3] = type_change
                s += 1
        else:
            anim_indexes[selected_index][3] = type_change

        update_table(anim_indexes,selected_index)

    elif event == 'edit_type_data':
        type_data = values.get('new_type_data')
        print(type_data)
        print(selected_index)

        if type(selected_index) == list:
            s = 0
            while s < len(list(selected_index)):
                anim_indexes[selected_index[s]][4] = type_data
                s += 1
        else:
            anim_indexes[selected_index][4] = type_data

        update_table(anim_indexes,selected_index)
        

    elif event == 'combine':
        initial = selected_index[0]
        s = 1
        while s < len(selected_index):
            combiner = selected_index[s]
            anim_indexes[initial][0] = anim_indexes[initial][0]+', '+anim_indexes[combiner][0]
            anim_indexes[initial][1] = anim_indexes[initial][1]+', '+anim_indexes[combiner][1]
            anim_indexes[initial][2] = str(anim_indexes[initial][2])+', '+str(anim_indexes[combiner][2])
            s += 1
            
        update_table(anim_indexes,selected_index)

    elif event == 'invert':
        if type(selected_index) == list:
            s = 0
            while s < len(list(selected_index)):
                if anim_indexes[selected_index[s]][5] == 'False':
                    anim_indexes[selected_index[s]][5] = 'True'
                else:
                    anim_indexes[selected_index[s]][5] = 'False'
                s += 1
        else:
            if anim_indexes[selected_index][5] == 'False':
                anim_indexes[selected_index][5] = 'True'
            else:
                anim_indexes[selected_index][5] = 'False'

        update_table(anim_indexes,selected_index)

    elif event == 'get_json_names':
        if checkFile(values.get('json_import_path')) == True:
            import_path = values.get('json_import_path')
            anim_indexes = getImportNames(import_path)
            update_table(anim_indexes,-1)

    elif event == 'json_save_file':
        save_name = values['json_save_name']
        save_path = values['json_save_path']
        if checkFolder(save_path) == True:
            writeAnimIndexes(anim_indexes,os.path.join(save_path,save_name+'.json'))

    elif event == 'Show Name Tracker':
        update_visibility({'Hide Name Tracker':True,'Name Table Layout':True,'Show Name Tracker':False})
        
    elif event == 'Hide Name Tracker':
        update_visibility({'Hide Name Tracker':False,'Name Table Layout':False,'Show Name Tracker':True})

    elif event == 'submit anims':
        bad_rows = []
        row = 0
        for a in anim_indexes:
            if a[3] != 'Character':
                if a[4] == '':
                    bad_rows.append(row)
            row += 1

        if len(bad_rows) == 0:

            dup_names = []
            names = []
            row = 0
            for a in anim_indexes:
                if a[1] not in names:
                    names.append(a[1])
                else:
                    dup_names.append(row)

                row += 1
            print(len(dup_names))
            
            if len(dup_names) == 0:
                if values['mugen_import'] == True:
                    update_visibility({'Anim Layout':False,'CE Layout':True,'Anim Name Layout':False})
                    if values['new_project'] == True:
                        update_visibility({'CE Entity Layout':False, 'CE Template Layout':True})
                        update_disabled({'Costumes File Path':True, 'Costumes File Browse':True})
                    else:
                        update_visibility({'CE Entity Layout':True, 'CE Template Layout':False})
                elif values['folder_import'] == True:
                    if values['new_project'] == True:
                        update_visibility({'Anim Layout':False,'Folder New CE Layout':True,'Anim Name Layout':False})
                    else:
                        update_visibility({'Anim Layout':False,'Folder CE Layout':True,'Anim Name Layout':False})

                writeAnimIndexes(anim_indexes,os.path.join('Files','System','Backup Anims.json'))
            else:
                sg.popup('Duplicate names detected!\nPlease change the selected row names!')
                update_table(anim_indexes,dup_names)

        else:
            sg.popup('Bad Rows Detected!\nPlease assign a value in the Type Data Column\nfor the highlighted rows')
            update_table(anim_indexes,bad_rows)

    elif event == 'Import Palettes':
        if values['Import Palettes'] == True:
            if values['new_project'] == True and values['mugen_import'] == True:
                update_disabled({'Base Palette Path':False,'Base Palette Browse':False,
                                 'Palette Files Path':False,'Palette Files Browse':False})
            else:
                update_disabled({'Base Palette Path':False,'Base Palette Browse':False,
                                 'Palette Files Path':False,'Palette Files Browse':False,
                                 'Costumes File Path':False, 'Costumes File Browse':False})
        else:
            update_disabled({'Base Palette Path':True,'Base Palette Browse':True,
                             'Palette Files Path':True,'Palette Files Browse':True,
                             'Costumes File Path':True, 'Costumes File Browse':True})

    elif event == 'submit ce':
        if values['only_palette'] == True:
            importPalette(values['Base Palette Path'],values['Palette Files Path'],values['Costumes File Path'])
            sg.popup('Palettes Imported!')
            window.close()
            break
        else:
            if values['new_project'] == True:
                checks = True
                if checkFolder(values['Mugen Template']) == True and checkFolder(values['Project Folder Path']) == True and checkFolder(values['Sprite Folder Path']) == True:

                    moveTemplate(values['Mugen Template'],values['Project Folder Path'],values['Sprite Folder Path'])
                    
                    folder_path = os.path.join(values['Project Folder Path'],'library','sprites')
                    moveSprites(folder_path, values['Sprite Folder Path'])
                    newImageSymbols(folder_path)
                    char_entity = os.path.join(values['Project Folder Path'],'library','entities','character.entity')
                    ce_data = getJSONData(char_entity)
                    #if values['Trim Sprites'] == True:
                    #    trimSprites(folder_path)
                    sprite_data, sprite_data_keys, image_align_x, image_align_y, sprite_names = getSpriteData(folder_path)
                    
                else:
                    checks = False
            else:
                checks = True
                if checkFile(values['Character Entity Path']) == True and checkFolder(values['Sprite Folder Path']) == True:
                    ce_data = getJSONData(values['Character Entity Path'])
                    sprite_data, sprite_data_keys, image_align_x, image_align_y, sprite_names = getSpriteData(values['Sprite Folder Path'])
                else:
                    checks = False

            if checks == True:
                hurt_check = values['Hurtboxes Check']
                hit_check = values['Hitboxes Check']
                projectiles = []
                for p in anim_indexes:
                    if p[3] == 'Projectile':
                        if p[4] not in projectiles:
                            projectiles.append(p[4])

                #print(projectiles)
                projectile_data = []
                for p in projectiles:
                    p_data = createProjectile(p, values['Project Folder Path'])
                    projectile_data.append(p_data)
                
                #print(projectiles)

                
                    
                
                if values["unaligned_check"] == True:
                    
                    groups = list(set([int(x.split('-')[0]) for x in sprite_data_keys if len(x.split('-')) > 1]))
                    
                    ffe_data,invalid_names = readFFE(values['ffe_file_path'],groups)
                    sprite_names.extend(invalid_names.keys())
                    #print(sprite_names)
                    
                    anim_data = getAnimData(anim_indexes, anim_lines, sprite_names, hurt_check, hit_check)
                    print(anim_data['wtf'])
                    
                    
                    for a in anim_data:
                        
                        temp_names = anim_data[a]['sprite_names']
                        
                        clean_names = []
                        for n in temp_names:
                            name_check = False
                            for invalid in invalid_names.keys():
                                if n == invalid:
                                    name_check = True
                                    clean_names.append(invalid_names[n])
                                    

                            if name_check == False:
                                clean_names.append(n)

                                
                        new_names = []
                        for t in clean_names:
                            if t != None:
                                new_names.append(t.replace('.meta',''))
                            else:
                                new_names.append('None')

                        
                        #sprite_pos = getSpritePosList(folder_path,new_names)
                        sprite_pos = getSpritePosFFE(new_names,ffe_data)

                        final_names = []
                        for n in new_names:
                            if a == 'wtf':
                                print(n)
                            if n != 'None':
                                final_names.append(n+'.meta')
                            else:
                                final_names.append(None)
                                
                        print(final_names)
                        anim_data[a]['sprite_names'] = final_names
                        anim_data[a]['sprite_pos'] = sprite_pos
                        
                    image_align_x = 0
                    image_align_y = 0
                        
                        
                        
                #print(anim_data)
                    print('here')
                    print(anim_data['wtf']['sprite_names'])
                else:
                    anim_data = getAnimData(anim_indexes, anim_lines, sprite_names, hurt_check, hit_check)
                    
                ce_data, projectile_data = editCE(ce_data,anim_data,sprite_data,sprite_data_keys,float(values['Scale-X']),float(values['Scale-Y']),image_align_x,image_align_y, projectile_data)
                
                if values['new_project'] == True:
                    writeNewCE(ce_data,char_entity)
                else:  
                    writeNewCE(ce_data,values['Character Entity Path'])
                for p in projectile_data:
                    writeNewCE(p,values['Project Folder Path']+'\\library\\entities\\'+p['id']+'.entity')

                if values['Import Palettes'] == True:
                    if values['new_project'] == True:
                        importPalette(values['Base Palette Path'],values['Palette Files Path'],os.path.join(values['Project Folder Path'],'library','costumes.palettes'))
                    else:
                        importPalette(values['Base Palette Path'],values['Palette Files Path'],values['Costumes File Path'])
                writeNewCE(anim_data,values['Project Folder Path']+'\\log.json')
                #if values['Animation Sprites'] == True:
                #    deleteSprites(folder_path,anim_data)
                window.close()
                sg.popup("Character Successfully Imported!")
            

    elif event == 'submit new ce folder':
        if checkFolder(values['Folder Template']) == True and checkFolder(values['Folder New']) == True:
            moveTemplate(values['Folder Template'],values['Folder New'],folder_path)
            folder_path = os.path.join(values['Folder New'],'library','sprites')
            newImageSymbols(folder_path)
            ce_data = getJSONData(os.path.join(values['Folder New'],'library','entities','character.entity'))
            master_sprite_data = {}
            master_sprite_data_keys = []
            anim_data = {}


            names = []
            for n in anim_indexes:
                names.append(n[1])
                
            for name in anim_indexes:
                anim_path = folder_path+'//'+name[1]
                if not os.path.exists(anim_path):
                    os.mkdir(anim_path)
                    old_path = folder_path+'//'+name[2]
                    file_count = 0
                    for f in os.listdir(old_path):
                        f_split = f.split('.')
                        f_split.pop()
                        file_extension = ''
                        for fs in f_split:
                            file_extension += fs

                        new_f = name[2]+'_'+str(file_count)+file_extension
                        os.rename(os.path.join(old_path,f),os.path.join(anim_path,new_f))

                    if name not in names:
                        os.remove(old_path)
                    
                sprite_data, sprite_data_keys, image_align_x, image_align_y, sprite_names = getSpriteData(folder_path+'\\'+name[2])
                for k,v in sprite_data.items():
                    master_sprite_data[k] = v
                master_sprite_data_keys.extend(sprite_data_keys)
                if values['new_folder_align_check'] == True:
                    sprite_pos = getSpritePos(folder_path+'\\'+name[2])
                    print(sprite_pos)
                else:
                    sprite_pos = [{'X':image_align_x,'Y':image_align_y} for x in sprite_data_keys]
                anim_data[name[1]] = {'sprite_names':sprite_names,
                                      'sprite_pos':sprite_pos,
                                      'frame_data':[1 for x in sprite_data_keys],
                                      'hurtbox_data':[[] for x in sprite_data_keys],
                                      'hitbox_data':[[] for x in sprite_data_keys],
                                      'type':[name[3],name[4]],
                                      'invert':name[5]
                                      }

            projectile_data = []
            
            ce_data, projectile_data = editCE(ce_data,anim_data,master_sprite_data,master_sprite_data_keys,float(values['Scale-X Folder New']),float(values['Scale-Y Folder New']),image_align_x,image_align_y,projectile_data)
            writeNewCE(ce_data,os.path.join(values['Folder New'],'library','entities','character.entity'))
            window.close()
            sg.popup("Character Successfully Imported!")
        

    elif event == 'submit ce folder':
        if checkFile(values['Character Entity Path Folder']) == True:
            if values['sprite_folder_check'] == False:
                sprite_folder = sg.popup_get_folder('Please enter the sprite folder for the project')
            
            ce_data = getJSONData(values['Character Entity Path Folder'])
            master_sprite_data = {}
            master_sprite_data_keys = []
            anim_data = {}

            names = []
            for n in anim_indexes:
                names.append(n[1])
                
            for name in anim_indexes:
                if values['sprite_folder_check'] == False:
                    anim_path = sprite_folder+'//'+name[1]
                else:
                    anim_path = folder_path+'//'+name[1]
                print(anim_path)
                if not os.path.exists(anim_path):
                    os.mkdir(anim_path)
                    old_path = folder_path+'//'+name[2]
                    file_count = 0
                    for f in os.listdir(old_path):
                        f_split = f.split('.')
                        f_split.pop()
                        file_extension = ''
                        for fs in f_split:
                            file_extension += fs

                        new_f = name[2]+'_'+str(file_count)+file_extension
                        os.rename(os.path.join(old_path,f),os.path.join(anim_path,new_f))

                    if name not in names:
                        os.remove(old_path)
                    
                sprite_data, sprite_data_keys, image_align_x, image_align_y, sprite_names = getSpriteData(folder_path+'\\'+name[2])
                for k,v in sprite_data.items():
                    master_sprite_data[k] = v
                master_sprite_data_keys.extend(sprite_data_keys)
                if values['folder_align_check'] == True:
                    sprite_pos = getSpritePos(folder_path+'\\'+name[2])
                    print(sprite_pos)
                else:
                    sprite_pos = [{'X':image_align_x,'Y':image_align_y} for x in sprite_data_keys]
                anim_data[name[1]] = {'sprite_names':sprite_names,
                                      'sprite_pos':sprite_pos,
                                      'frame_data':[1 for x in sprite_data_keys],
                                      'hurtbox_data':[[] for x in sprite_data_keys],
                                      'hitbox_data':[[] for x in sprite_data_keys],
                                      'type':[name[3],name[4]],
                                      'invert':name[5]
                                      }

            projectile_data = []
            print(anim_data)
            ce_data, projectile_data = editCE(ce_data,anim_data,master_sprite_data,master_sprite_data_keys,float(values['Scale-X Folder']),float(values['Scale-Y Folder']),image_align_x,image_align_y,projectile_data)
            writeNewCE(ce_data,values['Character Entity Path Folder'])
            window.close()
            sg.popup("Character Successfully Imported!")
        
        
        

    
