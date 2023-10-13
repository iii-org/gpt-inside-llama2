// 伺服器端 API 的 URL
const apiUrl = "http://127.0.0.1/__api/gpt/qa";

// 取得對話區塊元素
const conversationBody = document.getElementById("conversationBody");

// 取得問題輸入框元素
const questionInput = document.getElementById("question");

//取得參考資料label文字
var ref_label_text =  document.getElementById("ref_label").innerText;

// 監聽輸入框的按鍵事件
questionInput.addEventListener("keydown", function(event) {
  // 判斷是否按下 Enter 鍵
  if (event.key === "Enter") {
    if (!isComposing) {
      event.preventDefault(); // 避免觸發預設的 Enter 事件

      // 呼叫送出問題的函式
      submitQuestion();
    }
  }
});

var isComposing = false;

// 監聽中文輸入的 CompositionEvent
questionInput.addEventListener("compositionstart", function() {
  isComposing = true;
});

questionInput.addEventListener("compositionend", function() {
  isComposing = false;
});

// 清除對話視窗
function clearConversation() {
  // 將對話視窗內容清空
  conversationBody.innerHTML = "";
  document.getElementById('ref_label').innerHTML = "";
  ref_label_text = document.getElementById("ref_label").innerText;

}



// 送出問題的函式
function submitQuestion() {
  var question = questionInput.value.trim();

  if (question !== "") {
    var userQuestionWrapper = document.createElement("div");
    userQuestionWrapper.className = "text-right";
    var userQuestionText = document.createElement("p");
    userQuestionText.className = "user-question";
    userQuestionText.innerText = "使用者：\n" + question;
    userQuestionWrapper.appendChild(userQuestionText);
    conversationBody.appendChild(userQuestionWrapper);
    conversationBody.scrollTop = conversationBody.scrollHeight;
    questionInput.value = "";

    setTimeout(function() {
      var typingIndicatorWrapper = document.createElement("div");
      typingIndicatorWrapper.className = "text-left typing-indicator";
      var typingIndicator = document.createElement("p");
      typingIndicator.className = "text-muted";
      typingIndicator.innerHTML = '機器人：<br><span class="typing-text">輸入中 ...</span>';
      typingIndicatorWrapper.appendChild(typingIndicator);
      conversationBody.appendChild(typingIndicatorWrapper);
      conversationBody.scrollTop = conversationBody.scrollHeight;


      if (question.startsWith("參考資訊：")) {
        document.getElementById('ref_label').innerHTML = question;
        ref_label_text =  document.getElementById("ref_label").innerText;
        answer = "謝謝您的參考資訊，我知道了。";

        conversationBody.removeChild(typingIndicatorWrapper);
        var botAnswerWrapper = document.createElement("div");
        botAnswerWrapper.className = "text-left";
        var botAnswerText = document.createElement("p");
        botAnswerText.className = "bot-answer";
        botAnswerText.innerText = "機器人： \n" + answer;
        botAnswerWrapper.appendChild(botAnswerText);
        conversationBody.appendChild(botAnswerWrapper);

        var lineBreak = document.createElement("br");
        conversationBody.appendChild(lineBreak);

        conversationBody.scrollTop = conversationBody.scrollHeight;
      }
      else {
        //截取參考資料
        var refText = null;
        if (ref_label_text!=""){
          refText = ref_label_text.split('參考資訊：')[1];
        }

        callAPI(question, refText)
          .then(function(answer) {
            conversationBody.removeChild(typingIndicatorWrapper);
            var botAnswerWrapper = document.createElement("div");
            botAnswerWrapper.className = "text-left";
            var botAnswerText = document.createElement("p");
            botAnswerText.className = "bot-answer";
            botAnswerText.innerText = "機器人： \n" + answer;
            botAnswerWrapper.appendChild(botAnswerText);
            conversationBody.appendChild(botAnswerWrapper);

            var lineBreak = document.createElement("br");
            conversationBody.appendChild(lineBreak);

            conversationBody.scrollTop = conversationBody.scrollHeight;
          })
          .catch(function(error) {
            console.log("發生錯誤:", error);
          });
      }
    }, 600); // 0.6 秒延遲後顯示「機器人：輸入中」
  }
}

// 呼叫後端 API 的函式
function callAPI(question, refText) {
  return new Promise(function(resolve, reject) {
    const requestBody = {
      user_input: question,
      "temperature":0.9,
      "ref_threshold": 0.3,
      "top_p": 0.6,
      "top_k": 100,
      "repetition_penalty": 1.1,
      "gen_tokens": 512
    };
    if (refText !== null) {
      requestBody.reference = refText;
    }
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    })
      .then(function(response) {
        return response.json();
      })
      .then(function(data) {
        var answer = data.result.A[0];
        resolve(answer);
      })
      .catch(function(error) {
        console.log("發生錯誤:", error);
        resolve("不好意思，我正在忙錄中 ... 請您稍候再嘗試，謝謝。");
      });
  });
}


// 呼叫後端 GET API 的函式
function GETAPI(question) {
  return new Promise(function(resolve, reject) {
    // 發送 API 請求，使用 question 作為參數
    // 這裡使用示例中的假設 API 網址 apiUrl
    // 請根據您實際的後端 API 網址進行修改
    fetch(apiUrl + "?question=" + encodeURIComponent(question))
      .then(function(response) {
        return response.json();
      })
      .then(function(data) {
        // 從 API 回傳的資料中取得答案
        var answer = data.result.A[0];

        // 將答案回傳給呼叫的地方
        resolve(answer);
      })
      .catch(function(error) {
        // 若發生錯誤，將錯誤回傳給呼叫的地方
        reject(error);
      });
  });
}


