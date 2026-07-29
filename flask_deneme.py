from flask import Flask, request, jsonify
 
app = Flask(__name__)
 
# 1. GET İsteği: Sadece bilgi okumak için kullanılır.
@app.route('/bilgi', methods=['GET'])
def bilgi_getir():
    # Tarayıcıdan bu linke girince bu mesaj dönecek
    return jsonify({"mesaj": "Merhaba! Bu bir GET isteğidir. Menüyü getirdim."})
 
 
# 2. POST İsteği: Sunucuya veri (örneğin kullanıcı bilgisi, sipariş) göndermek için kullanılır.
@app.route('/chat', methods=['POST'])
def chat():
    # Kullanıcının bize gönderdiği veriyi (JSON formatında) alıyoruz
    gelen_veri = request.get_json()
 
    # Gönderilen verinin içinde 'yemek' diye bir bilgi var mı diye bakıyoruz
    answer = gelen_veri.get("yemek")
 
    # Gelen veriye göre cevap dönüyoruz
    return jsonify({
        "mesaj": f"Harika, {answer} siparişin mutfağa iletildi!",
        "durum": "Başarılı"
    })

if __name__ == '__main__':
    # Kod çalıştırıldığında sunucu 5000 portunda ayağa kalkar
    app.run(debug=True, port=5000)