# OpenAI Feed Trans
 <a href="README.md">English</a> | 中文

`Ver 0.1`

最近 openai-gtp3.5-turbo 的 API 出来之后，在想如果用来将原来读起来很吃力的外文 RSS 自动翻译，并使用我的 RSS 阅读器以订阅的方式看更新，是不是非常方便。因为刚刚接触 Python，所以又试着让 chatGPT 帮我生成一些代码。经过几天的捣鼓，它竟然可以工作！

如果有人也希望翻译 RSS，且有自己的 www 服务器，欢迎食用。请注意，OpenAI Feed Trans 只作为个人使用的小工具。不要公开经过你翻译的订阅源，因为可能引起版权问题。

使用时，你需要有自己的 OpenAI API-KEY。

# 基本功能

- 读取一个远程的 RSS Feed
- 使用 OpenAI 进行整个 Feed 的翻译，并保留 RSS 内原有样式
- 翻译后生成新的 Feed，保存到指定路径（ 比如 wwwroot ）
- 配合系统定时任务，可定时查询源 Feed 是否更新。有缓存功能，所以只会翻译新的 Entry，不会重复消耗 Tokens
- 运行失败时，没有完成的翻译会断点续翻
- Log 会记录所有消耗的 Tokens

# 使用方式
- 安装 `python 3.10`（其他版本并未测试）
- 安装依赖 `pip install -r requirements.txt` （也可在虚拟环境）
- 修改 `config.ini` 进行配置，请确保工作目录具备相应读写权限
- `python3 src/main.py`
- 设置系统定时任务，自动查询源 Feed 实现自动翻译更新

