from PIL import Image, ImageDraw, ImageFont
from urllib.request import urlopen
import time
import random
import base64
from io import BytesIO
import json
import boto3
import os

#Creates a challenge to be completed by the user to retreive contact info

#sets table_name from environment variable
table_name = os.environ['tableName']

client = boto3.client('dynamodb')

def lambda_handler(event, context):

    #Set vars from event context
    requestId = event['requestContext']['extendedRequestId']

    #randomly choose operator - ivision is hard for some so exclude it
    def rand_operator():
        operators = ["x", "+", "-"]

        return random.choice(operators)

    #randomly choose digits - 0 and 1 are too easy
    def rand_dig ():
        digits = [2, 3, 4, 5, 6, 7, 8, 9]

        return random.choice(digits)

    #generates a simple math problem
    def gen_problem(dig1, dig2, operator):
        if operator == "-" and dig1 < dig2:
            temp = dig1
            dig1 = dig2
            dig2 = temp
            solution = dig1 - dig2
        elif operator == "+":
            solution = dig1 + dig2
        elif operator == "x":
            solution = dig1 * dig2
        else:
            solution = dig1 - dig2

        problem = str(dig1) + operator + str(dig2)

        return problem, solution

    #creates a problem and solution
    problem, solution = gen_problem(rand_dig(), rand_dig(), rand_operator())

    #colors by name available for converting problem to image
    color_list = [
        'aliceblue', 'antiquewhite', 'aqua', 'aquamarine', 'azure', 
        'beige', 'bisque', 'black', 'blanchedalmond', 'blue', 
        'blueviolet', 'brown', 'burlywood', 'cadetblue', 'chartreuse', 
        'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson', 
        'cyan', 'darkblue', 'darkcyan', 'darkgoldenrod', 'darkgray', 
        'darkgrey', 'darkgreen', 'darkkhaki', 'darkmagenta', 
        'darkolivegreen', 'darkorange', 'darkorchid', 'darkred', 
        'darksalmon', 'darkseagreen', 'darkslateblue', 'darkslategray', 
        'darkslategrey', 'darkturquoise', 'darkviolet', 'deeppink', 
        'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue', 'firebrick', 
        'floralwhite', 'forestgreen', 'fuchsia', 'gainsboro', 
        'ghostwhite', 'gold', 'goldenrod', 'gray', 'grey', 'green', 
        'greenyellow', 'honeydew', 'hotpink', 'indianred', 'indigo', 
        'ivory', 'khaki', 'lavender', 'lavenderblush', 'lawngreen', 
        'lemonchiffon', 'lightblue', 'lightcoral', 'lightcyan', 
        'lightgoldenrodyellow', 'lightgreen', 'lightgray', 'lightgrey', 
        'lightpink', 'lightsalmon', 'lightseagreen', 'lightskyblue', 
        'lightslategray', 'lightslategrey', 'lightsteelblue', 
        'lightyellow', 'lime', 'limegreen', 'linen', 'magenta', 
        'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid', 
        'mediumpurple', 'mediumseagreen', 'mediumslateblue', 
        'mediumspringgreen', 'mediumturquoise', 'mediumvioletred', 
        'midnightblue', 'mintcream', 'mistyrose', 'moccasin', 
        'navajowhite', 'navy', 'oldlace', 'olive', 'olivedrab', 
        'orange', 'orangered', 'orchid', 'palegoldenrod', 'palegreen', 
        'paleturquoise', 'palevioletred', 'papayawhip', 'peachpuff', 
        'peru', 'pink', 'plum', 'powderblue', 'purple', 'rebeccapurple', 
        'red', 'rosybrown', 'royalblue', 'saddlebrown', 'salmon', 
        'sandybrown', 'seagreen', 'seashell', 'sienna', 'silver', 
        'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow', 
        'springgreen', 'steelblue', 'tan', 'teal', 'thistle', 'tomato', 
        'turquoise', 'violet', 'wheat', 'white', 'whitesmoke', 
        'yellow', 'yellowgreen']

    #font url to use for problem
    font_url = "https://github.com/googlefonts/roboto/blob/main/src/hinted/Roboto-Regular.ttf?raw=true"

    #use the font
    use_font = ImageFont.truetype(urlopen(font_url), 40)

    #size for problem
    W, H = (200,100)

    #set a background color randomly from color_list
    background_color = random.choice(color_list)

    #remove background color from list to prevent characters becoming invisible
    color_list.remove(background_color)

    #create the background image
    img = Image.new('RGB', (W,H), color = background_color)
        
    #draw tge background image
    draw = ImageDraw.Draw(img)

    #set the text size
    def size(t):
        w, h = draw.textsize(t, font=use_font)
        return w, h

    #initialize width, height, and width_list outside loop
    w = 0
    h = 0
    w_list = []

    #loop through problem get w and h of each character - set h to the highest character height
    #set w to the sum of all character widths
    for n in problem:
        wx, hy = size(n)
        w += wx
        w_list.append(wx)
        if hy > h:
            h = hy

    sum_prev_w = 0

    #loop through problem, set a color for each character and draw them
    for i, n in enumerate(problem):
        n_color = random.choice(color_list)
        color_list.remove(n_color)
        draw.text(((W-w)/2+sum_prev_w,(H-h)/2), n, font=use_font, fill=n_color)
        sum_prev_w += w_list[i]

    #convert image to base64 so it can be inserted into frontend
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    #5 minute timeout to solve problem
    expire_epoch = int(time.time()) + 300

    #add problem to DynamoDB table
    update_total = client.put_item(
        TableName=table_name,
        Item={
            'reqId': {
                'S': str(requestId)
            },
            'solution': {
                'N': str(solution)
            },
            'expiration': {
                'N' : str(expire_epoch)
            }
        }
    )

    #return the base64 encoded image string and the requestId
    response = {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*.mattisz.com/*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'problem' : img_b64,
            'reqId' : requestId
        })
    }
        
    return response