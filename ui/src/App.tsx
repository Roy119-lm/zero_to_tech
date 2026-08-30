import {
  createSignal,
  createResource,
  For,
  Show,
  createMemo,
  batch,
} from "solid-js";

const API_BASE = "/api/v1/metrics";

function App() {
  // --------------------------------------------------------------------------
  // 1. 状态管理：上传部分
  // --------------------------------------------------------------------------
  const [file, setFile] = createSignal(null);
  const [coarseMode, setCoarseMode] = createSignal("divide");
  const [insertMode, setInsertMode] = createSignal("overwrite");
  const [uploading, setUploading] = createSignal(false);
  const [uploadMsg, setUploadMsg] = createSignal({ type: "", text: "" });

  const handleFileChange = (e) => {
    if (e.target.files) setFile(e.target.files[0]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file()) {
      setUploadMsg({ type: "error", text: "请选择文件" });
      return;
    }
    setUploading(true);
    setUploadMsg({ type: "", text: "" });

    const formData = new FormData();
    formData.append("file", file());
    const url = new URL(`${API_BASE}/data`, window.location.origin);
    url.searchParams.append("coarse_data_mode", coarseMode());
    url.searchParams.append("insert_mode", insertMode());

    try {
      const res = await fetch(url.toString(), {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }
      setUploadMsg({ type: "success", text: "上传成功！任务已后台运行。" });
      setFile(null);
      refetchData(); // 上传成功刷新表格
    } catch (err) {
      setUploadMsg({ type: "error", text: err.message });
    } finally {
      setUploading(false);
    }
  };

  // --------------------------------------------------------------------------
  // 2. 状态管理：字典与级联 (高性能前端过滤)
  // --------------------------------------------------------------------------
  // 一次性获取全量字典
  const [fullDictionary] = createResource(async () => {
    const res = await fetch(`${API_BASE}/dictionary`);
    if (!res.ok) return [];
    return await res.json();
  });

  // UI 临时选择状态
  const [l1, setL1] = createSignal("");
  const [l2, setL2] = createSignal("");
  const [l3, setL3] = createSignal("");
  const [l4, setL4] = createSignal("");
  const [region, setRegion] = createSignal("");
  const [startTs, setStartTs] = createSignal("");
  const [endTs, setEndTs] = createSignal("");

  // 级联计算属性
  const l1Options = () =>
    [...new Set(fullDictionary()?.map((d) => d.l1_name))].filter(Boolean);
  const l2Options = () => {
    const currentL1 = l1();
    if (!currentL1) return [];
    return [
      ...new Set(
        fullDictionary()
          ?.filter((d) => d.l1_name === currentL1)
          .map((d) => d.l2_name),
      ),
    ].filter(Boolean);
  };
  const l3Options = createMemo(() => {
    const currentL1 = l1(),
      currentL2 = l2();
    if (!currentL2) return [];
    return [
      ...new Set(
        fullDictionary()
          ?.filter((d) => d.l1_name === currentL1 && d.l2_name === currentL2)
          .map((d) => d.l3_name),
      ),
    ].filter(Boolean);
  });
  const l4Options = createMemo(() => {
    const currentL1 = l1(),
      currentL2 = l2(),
      currentL3 = l3();
    if (!currentL3) return [];
    return [
      ...new Set(
        fullDictionary()
          ?.filter(
            (d) =>
              d.l1_name === currentL1 &&
              d.l2_name === currentL2 &&
              d.l3_name === currentL3,
          )
          .map((d) => d.l4_name),
      ),
    ].filter(Boolean);
  });

  // --------------------------------------------------------------------------
  // 3. 状态管理：查询部分
  // --------------------------------------------------------------------------
  const [queryParams, setQueryParams] = createSignal(null);

  const [dataResource, { refetch: refetchData }] = createResource(
    queryParams,
    async (q) => {
      const params = new URLSearchParams();
      if (q.l1) params.append("l1_name", q.l1);
      if (q.l2) params.append("l2_name", q.l2);
      if (q.l3) params.append("l3_name", q.l3);
      if (q.l4) params.append("l4_name", q.l4);
      if (q.region) params.append("region", q.region);
      if (q.start_ts) {
        params.append("start_ts", new Date(q.start_ts).toISOString());
      }
      if (q.end_ts) {
        params.append("end_ts", new Date(q.end_ts).toISOString());
      }

      const res = await fetch(`${API_BASE}/data?${params.toString()}`);
      if (!res.ok) throw new Error("Query failed");
      return await res.json();
    },
  );

  const handleSearch = (e) => {
    e.preventDefault();
    const selection = {
      l1: l1(),
      l2: l2(),
      l3: l3(),
      l4: l4(),
      start_ts: startTs(),
      end_ts: endTs(),
      region: region(),
    };
    setQueryParams(selection);
  };

  return (
    <div class="min-h-screen bg-gray-50 p-8 font-sans text-gray-800">
      <div class="max-w-7xl mx-auto space-y-8">
        <h1 class="text-3xl font-bold text-blue-700 border-b pb-4">
          指标数据管理平台
        </h1>

        {/* ------------------- 上传区域 ------------------- */}
        <section class="bg-white p-6 rounded-lg shadow-md">
          <h2 class="text-xl font-semibold mb-4">数据导入 (Excel/CSV)</h2>
          <form onSubmit={handleUpload} class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  选择文件
                </label>
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileChange}
                  class="block w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  年度数据分割模式
                </label>
                <select
                  value={coarseMode()}
                  onChange={(e) => setCoarseMode(e.target.value)}
                  class="w-full border p-2 rounded-md"
                >
                  <option value="divide">均匀分配 (Divide)</option>
                  <option value="equal">恒等变换 (Equal)</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  写入模式
                </label>
                <select
                  value={insertMode()}
                  onChange={(e) => setInsertMode(e.target.value)}
                  class="w-full border p-2 rounded-md"
                >
                  <option value="overwrite">覆盖 (Overwrite)</option>
                  <option value="append">追加 (Append)</option>
                </select>
              </div>
            </div>
            <div class="flex items-center gap-4">
              <button
                type="submit"
                disabled={uploading()}
                class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-md disabled:opacity-50 transition-colors"
              >
                {uploading() ? "上传中..." : "开始上传"}
              </button>
              <Show when={uploadMsg().text}>
                <span
                  class={`text-sm ${uploadMsg().type === "error" ? "text-red-600" : "text-green-600"}`}
                >
                  {uploadMsg().text}
                </span>
              </Show>
            </div>
          </form>
        </section>

        {/* ------------------- 查询区域 ------------------- */}
        <section class="bg-white p-6 rounded-lg shadow-md">
          <h2 class="text-xl font-semibold mb-4">智能指标查询</h2>
          <form
            onSubmit={handleSearch}
            class="bg-gray-50 p-4 rounded border border-gray-200"
          >
            {/* 级联指标选择 */}
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div class="flex flex-col gap-1">
                <label class="text-xs font-bold text-gray-500">一级指标</label>
                <select
                  value={l1()}
                  onChange={(e) =>
                    batch(() => {
                      setL1(e.target.value);
                      setL2("");
                      setL3("");
                      setL4("");
                    })
                  }
                  class="input-field"
                >
                  <option value="">全部</option>
                  <For each={l1Options()}>
                    {(opt) => <option value={opt}>{opt}</option>}
                  </For>
                </select>
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-xs font-bold text-gray-500">二级指标</label>
                <select
                  disabled={!l1()}
                  value={l2()}
                  onChange={(e) =>
                    batch(() => {
                      setL2(e.target.value);
                      setL3("");
                      setL4("");
                    })
                  }
                  class="input-field"
                >
                  <option value="">全部</option>
                  <For each={l2Options()}>
                    {(opt) => <option value={opt}>{opt}</option>}
                  </For>
                </select>
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-xs font-bold text-gray-500">三级指标</label>
                <select
                  disabled={!l2()}
                  value={l3()}
                  onChange={(e) =>
                    batch(() => {
                      setL3(e.target.value);
                      setL4("");
                    })
                  }
                  class="input-field"
                >
                  <option value="">全部</option>
                  <For each={l3Options()}>
                    {(opt) => <option value={opt}>{opt}</option>}
                  </For>
                </select>
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-xs font-bold text-gray-500">四级指标</label>
                <select
                  disabled={!l3()}
                  value={l4()}
                  onChange={(e) => setL4(e.target.value)}
                  class="input-field font-semibold text-blue-700"
                >
                  <option value="">全部</option>
                  <For each={l4Options()}>
                    {(opt) => <option value={opt}>{opt}</option>}
                  </For>
                </select>
              </div>
            </div>

            {/* 时间与地区 */}
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <label class="text-xs text-gray-500 block mb-1">开始时间</label>
                <input
                  type="datetime-local"
                  class="input-field"
                  value={startTs()}
                  onInput={(e) => setStartTs(e.target.value)}
                />
              </div>
              <div>
                <label class="text-xs text-gray-500 block mb-1">结束时间</label>
                <input
                  type="datetime-local"
                  class="input-field"
                  value={endTs()}
                  onInput={(e) => setEndTs(e.target.value)}
                />
              </div>
              <div>
                <label class="text-xs text-gray-500 block mb-1">
                  行政区划代码
                </label>
                <input
                  type="number"
                  placeholder="如: 110000"
                  class="input-field"
                  value={region()}
                  onInput={(e) => setRegion(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              class="w-full md:w-auto bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-8 rounded transition-all"
            >
              立即查询
            </button>
          </form>

          {/* 表格展示部分 */}
          <div class="mt-6 overflow-x-auto">
            <Show when={dataResource.loading}>
              <div class="text-center py-10 text-gray-400">正在获取数据...</div>
            </Show>
            <Show when={!dataResource.loading && dataResource()}>
              {(data) => (
                <>
                  <div class="mb-2 text-sm text-gray-500 text-right">
                    找到 {data().length} 条记录
                  </div>
                  <table class="min-w-full divide-y divide-gray-200 border">
                    <thead class="bg-gray-100">
                      <tr>
                        <th class="table-head">时间</th>
                        <th class="table-head">行政区划</th>
                        <th class="table-head">指标名称</th>
                        <th class="table-head">数值</th>
                        <th class="table-head">备注</th>
                      </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                      <For each={data().slice(0, 100)}>
                        {(row) => (
                          <tr class="hover:bg-gray-50">
                            <td class="table-cell">
                              {new Date(row.ts).toLocaleString()}
                            </td>
                            <td class="table-cell text-xs">
                              {row.province} {row.city} {row.county}
                            </td>
                            <td class="table-cell font-medium">
                              {row.indicator_name}
                            </td>
                            <td class="table-cell text-blue-600 font-bold">
                              {Number(row.indicator_value).toFixed(2)}
                            </td>
                            <td class="table-cell text-gray-400 text-xs">
                              {row.extra_info}
                            </td>
                          </tr>
                        )}
                      </For>
                    </tbody>
                  </table>
                  <Show when={data().length > 100}>
                    <div class="mb-2 text-sm text-gray-500 text-right">
                      超过100条查询结果，为减少渲染开销，请缩减查询范围...
                    </div>
                  </Show>
                </>
              )}
            </Show>
          </div>
        </section>
      </div>

      <style>{`
        .input-field { @apply w-full border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none transition-all bg-white disabled:bg-gray-100; }
        .table-head { @apply px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider; }
        .table-cell { @apply px-6 py-4 whitespace-nowrap text-sm text-gray-700; }
      `}</style>
    </div>
  );
}

export default App;
