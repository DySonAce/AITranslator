var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// server.ts
var import_express = __toESM(require("express"), 1);
var import_path = __toESM(require("path"), 1);
var import_vite = require("vite");
var import_genai = require("@google/genai");
var import_dotenv = __toESM(require("dotenv"), 1);
import_dotenv.default.config();
var apiKey = process.env.GEMINI_API_KEY;
var ai = null;
if (apiKey) {
  ai = new import_genai.GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build"
      }
    }
  });
} else {
  console.warn("GEMINI_API_KEY not found in environment variables. Server will run with mocked translation capability.");
}
async function startServer() {
  const app = (0, import_express.default)();
  const PORT = 3e3;
  app.use(import_express.default.json());
  function getLangCode(lang) {
    if (!lang) return "auto";
    const l = lang.toLowerCase();
    if (l.includes("\u7E41\u9AD4\u4E2D\u6587") || l.includes("traditional")) return "zh-TW";
    if (l.includes("s-chinese") || l.includes("\u7B80\u4F53\u4E2D\u6587") || l.includes("simplified")) return "zh-CN";
    if (l.includes("english") || l.includes("\u82F1\u6587")) return "en";
    if (l.includes("japanese") || l.includes("\u65E5\u672C\u8A9E")) return "ja";
    if (l.includes("korean") || l.includes("\uD55C\uAD6D")) return "ko";
    if (l.includes("spanish") || l.includes("\u897F\u73ED\u7259")) return "es";
    if (l.includes("french") || l.includes("\u6CD5\u6587")) return "fr";
    if (l.includes("german") || l.includes("\u5FB7\u6587")) return "de";
    if (l.includes("italian") || l.includes("\u7FA9\u5927\u5229")) return "it";
    if (l.includes("russian") || l.includes("\u4FC4\u6587")) return "ru";
    if (l.includes("portuguese") || l.includes("\u8461\u8404\u7259")) return "pt";
    if (l.includes("vietnamese") || l.includes("\u8D8A\u5357")) return "vi";
    if (l.includes("thai") || l.includes("\u6CF0\u6587")) return "th";
    if (l.includes("indonesian") || l.includes("\u5370\u5C3C")) return "id";
    if (l.includes("turkish") || l.includes("\u571F\u8033\u5176")) return "tr";
    return "auto";
  }
  async function translateViaGoogle(text, sourceLang, targetLang) {
    const sourceCode = getLangCode(sourceLang);
    const targetCode = getLangCode(targetLang);
    const sl = sourceCode === "auto" ? "auto" : sourceCode;
    const tl = targetCode === "auto" ? "zh-TW" : targetCode;
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sl}&tl=${tl}&dt=t&q=${encodeURIComponent(text)}`;
    const response = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      }
    });
    if (!response.ok) {
      throw new Error(`Google Translate HTTP error! status: ${response.status}`);
    }
    const result = await response.json();
    if (Array.isArray(result) && result[0]) {
      return result[0].map((item) => item[0]).join("");
    }
    throw new Error("Invalid response structure from Google Translate");
  }
  app.post("/api/translate", async (req, res) => {
    const { text, sourceLang, targetLang, engine } = req.body;
    if (!text || text.trim() === "") {
      return res.json({ translated: "" });
    }
    if (engine && engine.includes("Google")) {
      try {
        const translatedText = await translateViaGoogle(text, sourceLang, targetLang);
        return res.json({ translated: translatedText });
      } catch (err) {
        console.error("Google Translation Error:", err);
      }
    }
    if (ai) {
      try {
        const prompt = `\u60A8\u662F\u4E00\u500B\u5C08\u696D\u7684\u3001\u9AD8\u7CBE\u5BC6\u5BE6\u6642\u6578\u5B57\u672C\u5730\u5316\u8207\u7FFB\u8B6F\u5F15\u64CE\u3002\u8ACB\u5C07\u4EE5\u4E0B\u6587\u672C\u5F9E\u300C${sourceLang}\u300D\u7FFB\u8B6F\u81F3\u300C${targetLang}\u300D\uFF1A

\u6587\u672C\u5167\u5BB9\uFF1A
${text}

\u898F\u5B9A\uFF1A
1. \u50C5\u8F38\u51FA\u7FFB\u8B6F\u5F8C\u7684\u6700\u7D42\u5167\u5BB9\u3002
2. \u56B4\u7981\u593E\u96DC\u4EFB\u4F55\u60A8\u7684\u5206\u6790\u3001\u81EA\u6211\u4ECB\u7D39\u3001\u79AE\u8C8C\u554F\u5019\u3001\u4EE5\u53CA\u300C\u4EE5\u4E0B\u662F\u7FFB\u8B6F\uFF1A\u300D\u7B49\u524D\u7F6E\u8A5E\u6216\u5F8C\u7F6E\u5099\u8A3B\u3002
3. \u4FDD\u6301\u539F\u6587\u672C\u7684\u6240\u6709\u6BB5\u843D\u683C\u5F0F\u3001\u4EE3\u78BC\u6846\u3001\u7B26\u865F\u53CA\u6392\u7248\u5F62\u5F0F\u3002`;
        const response = await ai.models.generateContent({
          model: "gemini-3.5-flash",
          contents: prompt,
          config: {
            systemInstruction: "You are a professional, high-performance translation and localization engine. Translate the source text accurately to the target language. Keep any formatting and structure unchanged. Do not state anything other than the exact translation."
          }
        });
        const translatedText = response.text || "";
        return res.json({ translated: translatedText });
      } catch (err) {
        console.error("Gemini Translation API Error:", err);
        try {
          console.log("Gemini failed, falling back to Google Translate...");
          const fallbackTranslated = await translateViaGoogle(text, sourceLang, targetLang);
          return res.json({ translated: fallbackTranslated });
        } catch (fallbackErr) {
          return res.status(500).json({ error: err.message || "\u7FFB\u8B6F\u5931\u6557" });
        }
      }
    } else {
      try {
        const fallbackTranslated = await translateViaGoogle(text, sourceLang, targetLang);
        return res.json({ translated: fallbackTranslated });
      } catch (err) {
        return res.json({
          translated: `[\u6A21\u64EC\u8B6F\u6587 (${engine || "Gemini"}): ${sourceLang} -> ${targetLang}]
${text}

(\u6CE8\u610F\uFF1A\u5075\u6E2C\u5230\u7CFB\u7D71\u79D8\u5BC6\u4E2D\u5C1A\u672A\u8A2D\u5B9A\u6216\u8F09\u5165 GEMINI_API_KEY\uFF0C\u4E14\u5099\u7528\u7DB2\u8DEF Google \u7FFB\u8B6F\u4EA6\u8D85\u6642\uFF0C\u6B63\u4F7F\u7528\u672C\u5730\u7AEF\u66AB\u5B58\u6E2C\u8A66\u3002)`
        });
      }
    }
  });
  app.get("/api/python-integration", (req, res) => {
    res.json({
      setupSteps: [
        "\u5B89\u88DD\u5B98\u65B9 SDK: pip install google-genai",
        "\u8A2D\u5B9A\u74B0\u5883\u8B8A\u91CF: export GEMINI_API_KEY='\u60A8\u7684\u5BC6\u9470'",
        "\u57F7\u884C python translate.py \u9032\u884C\u7FFB\u8B6F"
      ],
      pythonCode: `from google import genai
import os

def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    # \u8B80\u53D6\u74B0\u5883\u8B8A\u6578\u4E2D\u7684\u91D1\u9470
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("\u8ACB\u5148\u8A2D\u5B9A GEMINI_API_KEY \u74B0\u5883\u8B8A\u6578")
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"\u8ACB\u5C07\u4EE5\u4E0B\u6587\u672C\u5F9E {source_lang} \u7FFB\u8B6F\u6210 {target_lang}\u3002\u50C5\u8F38\u51FA\u8B6F\u5F8C\u7D14\u6587\u672C\uFF1A\\n\\n{text}"
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    return response.text

# \u6E2C\u8A66\u7528\u4F8B
if __name__ == "__main__":
    original = "Hello World! This is a real-time cyber translator integrated with Python."
    translatedStr = translate_text(original, "English", "Traditional Chinese")
    print("\u539F\u6587\u5B57\uFF1A", original)
    print("\u8B6F\u5F8C\u6587\uFF1A", translatedStr)
`
    });
  });
  if (process.env.NODE_ENV !== "production") {
    const vite = await (0, import_vite.createServer)({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = import_path.default.join(process.cwd(), "dist");
    app.use(import_express.default.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(import_path.default.join(distPath, "index.html"));
    });
  }
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[Cyber-Server] AI Translator runs on port ${PORT}`);
  });
}
startServer();
//# sourceMappingURL=server.cjs.map
