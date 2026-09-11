# Tutor TOGAF

## Descripción del proyecto

**Tutor TOGAF** es un asistente experto académico diseñado para apoyar a estudiantes de Ingeniería de Sistemas en el aprendizaje y comprensión del marco de arquitectura empresarial **TOGAF**.

El asistente utilizará técnicas de **Inteligencia Artificial, Prompt Engineering, Few-Shot Prompting** para responder preguntas relacionadas con los conceptos, fases, métodos y componentes de TOGAF a partir de una base de conocimiento académica.

El propósito principal es proporcionar un tutor personalizado que explique los conceptos de TOGAF de manera clara, estructurada y comprensible para estudiantes universitarios.

---

## Objetivo

Desarrollar un asistente académico capaz de responder preguntas sobre TOGAF, explicar conceptos complejos de manera sencilla y apoyar diferentes actividades de aprendizaje, utilizando como referencia material académico seleccionado.

El asistente busca complementar el proceso de aprendizaje del estudiante, permitiéndole realizar consultas sobre los contenidos de TOGAF y recibir explicaciones adaptadas a su nivel de comprensión.

---

## Tipo de asistente

**Tutor Académico Personalizado**

### Área de conocimiento

**Arquitectura Empresarial — TOGAF**

### Público objetivo

Estudiantes de Ingeniería de Sistemas y personas que estén iniciando su aprendizaje en Arquitectura Empresarial y TOGAF.

---


## Funcionalidades

El asistente estará diseñado para realizar las siguientes actividades:

* Responder preguntas relacionadas con TOGAF.
* Explicar conceptos técnicos utilizando lenguaje sencillo.
* Proporcionar ejemplos relacionados con situaciones empresariales.
* Comparar conceptos de TOGAF.
* Apoyar la preparación para evaluaciones.
* Indicar cuando la información disponible no es suficiente para responder una pregunta.
* Evitar inventar información que no esté sustentada en la base de conocimiento.
* Mantener respuestas estructuradas y consistentes.

---

## Base de conocimiento

El asistente será desarrollado para trabajar con una base de conocimiento especializada en TOGAF.

Esta base podrá incluir:

* Material académico de la asignatura.
* Guías de estudio.
* Documentos sobre TOGAF.
* Material relacionado con el ADM.

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone URL_DEL_REPOSITORIO
cd Tutor-TOGAF
```

### 2. Crear el entorno virtual

```
python -m venv .venv
```

### 3. Activar el entorno virtual

```
.\venv\Scripts\Activate
```

### 4. Instalar las dependencias

```
pip install -r requirements.txt
```

### 5. Configurar las variables de entorno

Crear un archivo `.env`:

```
GEMINI_API_KEY=tu_clave
```

### 6. Ejecutar el proyecto

```
python src/main.py
```

---
