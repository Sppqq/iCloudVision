from DeepImageSearch import Load_Data, Search_Setup
import os

def index_media():
    # Путь к папке с изображениями
    image_dir = "photos"
    
    # Создаем экземпляр для загрузки данных
    load_data = Load_Data()
    
    # Загружаем все изображения из директории
    image_list = load_data.from_folder([image_dir])
    
    # Настраиваем поиск
    st = Search_Setup(image_list=image_list, model_name="vgg16", pretrained=True)
    
    # Извлекаем особенности и сохраняем индекс
    st.run_index()
    
    print("Индексация завершена! Индекс сохранен в metadata/")

if __name__ == "__main__":
    index_media() 