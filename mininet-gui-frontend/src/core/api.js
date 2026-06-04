import axios from "axios";
import { backendHttpUrl } from "./config";

const baseUrl = backendHttpUrl;

export const deployHost = async (host) => {
  try {
    const response = await axios.post(baseUrl + "/api/mininet/hosts", host);
    return response.status === 200;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return false;
  }
};

export const deploySwitch = async (sw) => {
  try {
    const response = await axios.post(baseUrl + "/api/mininet/switches", sw);
    return response.status === 200;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return false;
  }
};

export const deployController = async (ctl) => {
  try {
    const payload = { ...ctl };
    if (payload.colorCode) {
      payload.color = payload.colorCode;
      delete payload.colorCode;
    }
    if (payload.color && typeof payload.color === "object") {
      delete payload.color;
    }
    const response = await axios.post(
      baseUrl + "/api/mininet/controllers",
      payload,
    );
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const getHealthStatus = async () => {
  try {
    const root = baseUrl?.endsWith("/api") ? baseUrl : `${baseUrl}/api`;
    const response = await axios.get(`${root}/health`);
    return response.data || null;
  } catch (error) {
    console.warn("Failed to fetch health status", error);
    return null;
  }
};

export const deployLink = async (src, dst) => {
  try {
    const response = await axios.post(baseUrl + "/api/mininet/links", [
      src,
      dst,
    ]);
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const assocSwitch = async (sw, ctl) => {
  try {
    const response = await axios.post(
      baseUrl + `/api/mininet/associate_switch`,
      {
        switch: sw,
        controller: ctl,
      },
    );
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const deleteNode = async (nodeId) => {
  try {
    const response = await axios.delete(
      baseUrl + `/api/mininet/delete_node/${nodeId}`,
    );
    return response.status === 200;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const deleteLink = async (srcId, dstId) => {
  try {
    const response = await axios.delete(
      baseUrl + `/api/mininet/delete_link/${srcId}/${dstId}`,
    );
    return response.status === 200;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const getInterfaces = async () => {
  try {
    const response = await axios.get(baseUrl + "/api/mininet/interfaces");
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const getSnifferState = async () => {
  try {
    const response = await axios.get(baseUrl + "/api/mininet/sniffer/state");
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const getSnifferHistory = async () => {
  try {
    const response = await axios.get(baseUrl + "/api/mininet/sniffer/history");
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const startSniffer = async () => {
  try {
    const response = await axios.post(
      baseUrl + "/api/mininet/sniffer/start",
      null,
    );
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const stopSniffer = async () => {
  try {
    const response = await axios.post(
      baseUrl + "/api/mininet/sniffer/stop",
      null,
    );
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const exportSnifferPcap = async () => {
  try {
    const response = await axios.get(baseUrl + "/api/mininet/sniffer/export", {
      responseType: "blob",
    });
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const removeAssociation = async (srcId, dstId) => {
  try {
    const response = await axios.delete(
      baseUrl + `/api/mininet/remove_association/${srcId}/${dstId}`,
    );
    return response.status === 200;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const updateNodePosition = async (nodeId, position) => {
  try {
    const response = await axios.post(baseUrl + `/api/mininet/node_position`, {
      node_id: nodeId,
      position: position,
    });
    return response.status === 200;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const requestStartNetwork = async () => {
  try {
    const response = await axios.post(baseUrl + "/api/mininet/start", null);
    return response.status === 200;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return false;
  }
};

export const requestStopNetwork = async () => {
  try {
    const response = await axios.post(baseUrl + "/api/mininet/stop", null);
    return response.status === 200;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return false;
  }
};

export const requestFullResetNetwork = async () => {
  try {
    const response = await axios.post(
      baseUrl + "/api/mininet/full_reset",
      null,
    );
    return response.status === 200;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return false;
  }
};

export const requestExportNetwork = async () => {
  try {
    const response = await axios.get(baseUrl + "/api/mininet/export_json", {
      responseType: "blob",
    });

    if (response.status === 200) {
      const blob = new Blob([response.data], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "network_export.json";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
  }
};

export const requestImportNetwork = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await axios.post(
      baseUrl + "/api/mininet/import_json",
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );

    return response.data;
  } catch (error) {
    throw new Error(
      error.response ? error.response.data.detail : "Network Error",
    );
  }
};

export const requestRunPingall = async () => {
  try {
    const response = await axios.post(baseUrl + "/api/mininet/pingall", null);
    return response.data;
  } catch (error) {
    if (error.response?.status === 409) {
      return { running: true };
    }
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return false;
  }
};

export const runIperf = async (payload) => {
  try {
    const seconds = payload.seconds || 5;
    const timeoutMs = (seconds + 15) * 1000;
    const response = await axios.post(baseUrl + "/api/mininet/iperf", payload, {
      timeout: timeoutMs,
    });
    return response.data || null;
  } catch (error) {
    if (error.response?.status === 409) {
      return { running: true };
    }
    if (error.code === "ECONNABORTED") {
      alert("Iperf test timed out. The test may be stuck.");
      return null;
    }
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return null;
  }
};

export const sendGet = async (url) => {
  try {
    const response = await axios.get(url);
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return false;
  }
};

export const getHosts = async () => {
  return await sendGet(baseUrl + "/api/mininet/hosts");
};

export const updateHost = async (hostId, payload) => {
  try {
    const response = await axios.patch(
      baseUrl + `/api/mininet/hosts/${hostId}`,
      payload,
    );
    return response.data || null;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return null;
  }
};

export const getSwitches = async () => {
  return await sendGet(baseUrl + "/api/mininet/switches");
};

export const updateController = async (controllerId, payload) => {
  try {
    const body = { ...payload };
    if (body.colorCode) {
      body.color = body.colorCode;
      delete body.colorCode;
    }
    const response = await axios.put(
      baseUrl + `/api/mininet/controllers/${controllerId}`,
      body,
    );
    return response.data?.controller || null;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    return null;
  }
};

export const getEdges = async () => {
  return await sendGet(baseUrl + "/api/mininet/links");
};

export const getNodeStats = async (nodeId) => {
  return await sendGet(baseUrl + `/api/mininet/stats/${nodeId}`);
};

export const listFlows = async (switchId) => {
  try {
    const response = await axios.get(
      baseUrl + `/api/mininet/flows/${switchId}`,
    );
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const addFlow = async (flow) => {
  try {
    const response = await axios.post(baseUrl + "/api/mininet/flows", flow);
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const deleteFlows = async (flow) => {
  try {
    const response = await axios.delete(baseUrl + "/api/mininet/flows", {
      data: flow,
    });
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};

export const deleteFlowById = async (switchId, flowId) => {
  try {
    const response = await axios.delete(
      baseUrl + `/api/mininet/flows/${switchId}/${flowId}`,
    );
    return response.data;
  } catch (error) {
    alert(error.response ? error.response.data["detail"] : "Network Error");
    throw error;
  }
};
