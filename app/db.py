para base de datos
CREATE TABLE roles (
    id_rol INT PRIMARY KEY,
    nombre VARCHAR(50)
);

CREATE TABLE usuario (
    id_usuario INT PRIMARY KEY AUTO_INCREMENT,
    legajo INT,
    nombre VARCHAR(100),
    apellido VARCHAR(100),
    contraseña VARCHAR(255),
    rol_id INT,
    FOREIGN KEY (rol_id) REFERENCES roles(id_rol)
);

CREATE TABLE programa (
    id_programa INT PRIMARY KEY,
    nombre VARCHAR(100),
    numero VARCHAR(50)
);

CREATE TABLE oficina (
    id_oficina INT PRIMARY KEY,
    nombre VARCHAR(100)
);

CREATE TABLE notas (
    id INT PRIMARY KEY,
    id_usuario INT,
    anio YEAR,
    estado VARCHAR(50),
    id_programa INT,
    id_oficina INT,
    numero_oficina VARCHAR(50),
    detalle TEXT,
    fechaingreso DATE,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
    FOREIGN KEY (id_programa) REFERENCES programa(id_programa),
    FOREIGN KEY (id_oficina) REFERENCES oficina(id_oficina)
);

INSERT INTO roles (id_rol, nombre) VALUES (1, 'Administrador');                    
INSERT INTO roles (id_rol, nombre) VALUES (2, 'Usuario');