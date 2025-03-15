import random
import string

def modify_text(text, intelligence):
    if intelligence == 0:
        length = len(text)
        return ''.join(random.choice(string.ascii_letters + " ") for _ in range(length))
    elif intelligence == 100:
        return text
    else:
        if intelligence < 20:
            return modify_text(text, 0)
        elif 20 <= intelligence < 50:
            probability = (50 - intelligence) / 30
            modified_text = ''
            for char in text:
                if random.random() < probability:
                    modified_text += random.choice(string.ascii_letters + " ")
                else:
                    modified_text += char
            return modified_text
        elif 50 <= intelligence < 80:
            num_swaps = int((80 - intelligence) / 30 * len(text) / 2)
            text_list = list(text)
            for _ in range(max(1, num_swaps)):
                if len(text_list) < 2:
                    break
                i = random.randint(0, len(text_list) - 2)
                text_list[i], text_list[i + 1] = text_list[i + 1], text_list[i]
            return ''.join(text_list)
        elif 80 <= intelligence < 100:
            num_changes = int((100 - intelligence) / 20)
            text_list = list(text)
            for _ in range(max(1, num_changes)):
                if not text_list:
                    break
                index = random.randint(0, len(text_list) - 1)
                text_list[index] = random.choice(string.ascii_letters + " ")
            return ''.join(text_list)
        return text