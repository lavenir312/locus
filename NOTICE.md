# 致谢与来源声明

Locus 的规则不是凭空设计的。四原则里几乎每一条都能指到某个开源项目的某个文件。这份文件把借鉴关系、许可证状况、代码边界一次说清，免得后来人去猜。

## 一、借鉴了哪些项目

| 项目 | 地址 | 许可证 | 借鉴了什么 |
|---|---|---|---|
| learn-from-materials | github.com/dmoshehun-prog/learn-from-materials | MIT（© 2025 virgiliojr94，© 2026 contributors） | 逐块覆盖台账、双向映射、术语清单字段、三级递进讲解、出处强制格式 |
| dsh-deepread | github.com/xiehuan123/dsh-deepread | MIT（© 2026 xiehuan123） | 四档置信度（作者原意／原文事实／推断／无法确认）的分级方式 |
| fastReader | github.com/pf-sjtu/fastReader | 无许可证文件 | 「复述」与「评析」分离的章节摘要结构 |
| idlearn | github.com/diomir0/idlearn | 无许可证文件 | 作为**反面案例**：其逐层压缩流程会让尾注在中间层丢失，本工具据此把台账建在压缩之前 |

另有一项来自本机的一个书籍蒸馏 skill（非公开仓库），只借鉴了分层摘要 L1／L2／L3 的形态，未复制其内容。

逐条对应关系见 `references/sources.md`，那里每一项都写了出自哪个仓库的哪个文件。

## 二、借鉴的边界

**只借鉴设计思路与规则，没有复制代码。** 这不是一句免责声明，是逐行比对过的：

把本仓库 `scripts/` 下六个文件的每一行（长度 >25 字符、非注释）与上述四个仓库抓取到的 13,015 行去重代码逐行比对，**重合 12 行**，全部是 Python 样板：

```
ap = argparse.ArgumentParser()
if __name__ == '__main__':
os.makedirs(out_dir, exist_ok=True)
```

业务逻辑零重合。核验、门禁、拆章、构建这几个脚本都是为这个工具重写的——比如「术语回原文校验」这件事，四个项目里一个都没有，是本项目补的缺口。

## 三、关于两个没有许可证的项目

`fastReader` 与 `idlearn` 的仓库根目录下没有 LICENSE、COPYING 或任何版权声明文件。按伯尔尼公约，无许可证意味着保留所有权利，因此对本项目的处理方式如下：

- **没有使用它们的任何代码**（见上节比对结果）。
- 只参考了公开展示的设计思路。设计思路本身不构成著作权保护对象。
- `references/sources.md` 中对 idlearn 提示词的一句英文引用，是作为批评性证据使用（说明逐层压缩会吃掉细节），长度 6 个词，属于评论引用。对 fastReader 的部分是转述，非逐字引用。

如果这两个项目的作者认为有不妥，请开 issue，我会配合修改或删除相关表述。

## 四、许可证

本项目以 MIT 发布，见 `LICENSE`。

上面两个 MIT 项目（learn-from-materials、dsh-deepread）的版权声明保留在此，以符合 MIT 关于保留版权声明的要求：

```
Copyright (c) 2025 virgiliojr94
Copyright (c) 2026 learn-from-materials contributors

Copyright (c) 2026 xiehuan123
```

## 五、示例材料的来源

`examples/` 里的 `demo.txt` 是为演示而自撰的短文，`000_demo_note.md` 是对它的笔记。**没有使用任何在版图书的原文**，因此示例可以随仓库自由分发。
