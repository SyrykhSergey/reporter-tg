# Имя файла для сохранения строк
filename = 'output.txt'

# Открываем файл для записи
with open(filename, 'w') as file:
    # Генерируем строки от 1 до 1000
    for i in range(10000, 10999):
        line = f"185.162.130.86:{i}:1wqTc9R7StsrTKYSSXJu:RNW78Fm5"
        file.write(line + '\n')  # Записываем строку в файл и добавляем перевод строки

print(f"Файл '{filename}' успешно создан и содержит 1000 строк.")
