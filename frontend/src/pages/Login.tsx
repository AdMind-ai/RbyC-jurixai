// src/pages/Login.tsx
import { useState, useContext } from "react";
import { AuthContext } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";
import { useTheme } from "@mui/material";
import { CSSProperties } from "react";
import { CircularProgress } from "@mui/material";
import { toast } from "react-toastify";

const Login: React.FC = () => {
  // const [username, setUsername] = useState("");
  const [email, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const auth = useContext(AuthContext);
  const navigate = useNavigate();
  const theme = useTheme();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (auth) {
        const success = await auth.login(email, password);
        if (success) {
          navigate("/");
        } else {
          navigate("/login");
          toast.error("Invalid email or password.");
        }
      }
    } catch (error) {
      alert("An error occurred while logging in.");
      console.error("Error logging in:", error);
    } finally {
      setLoading(false);
    }
  };

  const styles: { [key: string]: CSSProperties } = {
    container: {
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      height: "100vh",
      fontFamily: "Arial, sans-serif",
      backgroundColor: theme.palette.background.paper,
    },
    loginContainer: {
      borderRadius: "16px",
      padding: "40px",
      boxShadow: "0px 2px 15px #00000040",
      textAlign: "center" as const,
      width: "340px",
      backgroundColor: theme.palette.background.default,
    },
    form: {
      display: "flex",
      flexDirection: "column",
    },
    label: {
      textAlign: "left" as const,
      marginBottom: "5px",
      color: "#777",
    },
    input: {
      marginBottom: "15px",
      padding: "12px",
      borderRadius: "10px",
      border: "1px solid #ddd",
      backgroundColor: "#f7f7f7",
      color: "#333",
      outline: "none",
    },
    recover: {
      textAlign: "right" as const,
      color: "#999",
      textDecoration: "none",
      fontSize: "12px",
      marginBottom: "20px",
    },
    button: {
      padding: "12px",
      borderRadius: "10px",
      border: "none",
      color: "#FFF",
      fontSize: "22px",
      fontWeight: "bold",
      cursor: "pointer",
      backgroundColor: theme.palette.primary.main,
    },
    loginLogo: {
      width: "200px", 
      marginBottom: "20px",
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.loginContainer}>
        <img
          src={`/logo.png`} 
          alt="Login Logo"
          style={styles.loginLogo}
        />
        <form style={styles.form} onSubmit={handleSubmit}>
          <label style={styles.label}>Email</label>
          <input
            style={styles.input}
            type="text"
            placeholder="Email"
            onChange={(e) => setUsername(e.target.value)}
          />
          <label style={styles.label}>Password</label>
          <input
            style={styles.input}
            type="password"
            placeholder="Password"
            onChange={(e) => setPassword(e.target.value)}
          />

          <Link to="/forgot-password" style={styles.recover}>
            Forgot password?
          </Link>

          <button style={styles.button}>
            {loading ? <CircularProgress size={22} color="inherit" /> : "Login"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;