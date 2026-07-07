<!doctype html>
<html lang="zh-CN">
  <head>
    <script>
      (function (w, d, u, b, n, pc, ga, ae, po, s, p, e, t, pp) {
        pc = "precollect";
        ga = "getAttribute";
        ae = "addEventListener";
        po = "PerformanceObserver";
        s = function (m) {
          p = [].slice.call(arguments);
          p.push(Date.now(), location.href);
          (m == pc ? s.p.a : s.q).push(p);
        };
        s.q = [];
        s.p = { a: [] };
        w[n] = s;
        e = document.createElement("script");
        e.src = u + "?bid=" + b + "&globalName=" + n;
        e.crossOrigin =
          u.indexOf("sdk-web") > 0 ? "anonymous" : "use-credentials";
        d.getElementsByTagName("head")[0].appendChild(e);
        if (ae in w) {
          s.pcErr = function (e) {
            e = e || w.event;
            t = e.target || e.srcElement;
            if (t instanceof Element || t instanceof HTMLElement) {
              if (t[ga]("integrity")) {
                w[n](pc, "sri", t[ga]("href") || t[ga]("src"));
              } else {
                w[n](pc, "st", {
                  tagName: t.tagName,
                  url: t[ga]("href") || t[ga]("src"),
                });
              }
            } else {
              w[n](pc, "err", e.error);
            }
          };
          s.pcRej = function (e) {
            e = e || w.event;
            w[n](pc, "reject", e.reason || (e.detail && e.detail.reason));
          };
          w[ae]("error", s.pcErr, true);
          w[ae]("unhandledrejection", s.pcRej, true);
        }
        if ("PerformanceLongTaskTiming" in w) {
          pp = s.pp = { entries: [] };
          pp.observer = new PerformanceObserver(function (l) {
            pp.entries = pp.entries.concat(l.getEntries());
          });
          pp.observer.observe({ entryTypes: ["longtask"] });
        }
      })(
        window,
        document,
        "https://lf3-short.ibytedapm.com/slardar/fe/sdk-web/browser.cn.js",
        "clawhub_mirror",
        "Slardar",
      );
      window.Slardar("init", {
        bid: "clawhub_mirror",
      });
      window.Slardar('start');
    </script>
    <meta charset="UTF-8" />
    <link rel="icon" href="https://res.gcloudcache.com/volc-fe/cloudfe-clawhub/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>ClawHub 中国官方镜像站</title>
    <meta
      name="description"
      content="为国内开发者打造的 ClawHub 高速镜像服务。全量、实时同步 OpenClaw 官方技能包（Skills）与节点库，提供稳定、低延迟的拉取体验，彻底解决网络连通痛点，助力 AI 智能体高效开发。"
    />
    <meta
      name="keywords"
      content="ClawHub镜像, ClawHub国内源, ClawHub加速, 龙虾智能体, Skills下载, Skills安装, AI Agent插件, 技能包同步, 开发者工具镜像"
    />
    <link rel="canonical" href="https://cn.clawhub-mirror.com/" />
    <meta property="og:title" content="ClawHub 中国官方镜像站" />
    <meta
      property="og:description"
      content="为国内开发者打造的 ClawHub 高速镜像服务。全量、实时同步 OpenClaw 官方技能包（Skills）与节点库，提供稳定、低延迟的拉取体验，彻底解决网络连通痛点，助力 AI 智能体高效开发。"
    />
    <meta property="og:type" content="website" />
    <meta property="og:url" content="https://cn.clawhub-mirror.com/" />
    <meta
      property="og:image"
      content="https://cn.clawhub-mirror.com/clawd-logo.png"
    />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="ClawHub 中国官方镜像站" />
    <meta
      name="twitter:description"
      content="为国内开发者打造的 ClawHub 高速镜像服务。全量、实时同步 OpenClaw 官方技能包（Skills）与节点库，提供稳定、低延迟的拉取体验，彻底解决网络连通痛点，助力 AI 智能体高效开发。"
    />
    <meta
      name="twitter:image"
      content="https://cn.clawhub-mirror.com/clawd-logo.png"
    />
    <script>
      if (typeof Object.hasOwn !== "function") {
        Object.hasOwn = function hasOwn(object, property) {
          return Object.prototype.hasOwnProperty.call(object, property);
        };
      }
    </script>
    <script type="module" crossorigin src="https://res.gcloudcache.com/volc-fe/cloudfe-clawhub/assets/index-GaFyS6Xx.js"></script>
    <link rel="stylesheet" crossorigin href="https://res.gcloudcache.com/volc-fe/cloudfe-clawhub/assets/index-Cg9d3633.css">
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
