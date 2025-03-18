%% figFullrandom.m
%
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%
%   [+] Fecha: 10 Mar 2025
clc
close all
clear variables

% Ruta base donde están los resultados de full random
base_path = "../results/ieee123_fullrandom/";
root_folders = dir(fullfile(base_path, "root_*"));

% Inicializar matrices para almacenar datos de todos los roots
num_roots = length(root_folders);
num_deltas = 96; 
num_criteria = 4; 

% Matriz para almacenar los datos de todos los roots
data3d_all_roots = zeros(num_criteria, 13, num_deltas, num_roots);
data_power_all_roots = zeros(num_criteria, num_deltas, 3, num_roots);

for r = 1:num_roots
    root_path = fullfile(base_path, root_folders(r).name);
    
    for d = 0:num_deltas-1
        file_path = fullfile(root_path, strcat("csv/outdata_d", num2str(d), ".csv"));
        
        if exist(file_path, 'file')
            data_table = readtable(file_path, 'NumHeaderLines', 1);
            data = data_table{:,:};
            selected_criteria = [1, 3, 4, 5];
            data3d_all_roots(:, :, d+1, r) = data(selected_criteria, :);
            data_power_all_roots(:, d+1, :, r) = data(selected_criteria, [2 4 6]);
        end
    end
end

% Calcular promedio y desviación estándar
data_avg_all = mean(data3d_all_roots, 4);
sem_all = std(data3d_all_roots, [], 4) / sqrt(num_roots);

data_avg_power = mean(data_power_all_roots, 4);
sem_power = std(data_power_all_roots, [], 4) / sqrt(num_roots);

% Generar gráficos para los datos combinados
result_path = fullfile(base_path, "global_results/");
if ~exist(result_path, 'dir')
    mkdir(result_path);
end

%% FIGURA 1: Potencias
h1 = figure();
set(gcf, 'Position', [100, 100, 1200, 500]);

% Layout para minimizar espacios
tiledlayout(1,2, 'TileSpacing', 'loose', 'Padding', 'loose');

% Subplot 1 - Balance de Potencias Global
nexttile;
plotBarWithErrors(mean(data_avg_all(:, [2 4 6], :), 3), sem_all(:, [2 4 6], :), "Average Global Power Balance", "Power (kW)");

% Subplot 2 - Flujo absoluto de potencia
nexttile;
plotBarWithErrors(mean(data_avg_all(:, [3 5 7], :), 3), sem_all(:, [3 5 7], :), "Average Absolute value of Power-flow", "Power (kW)");

% Crear una leyenda global
hL1 = legend("Ideal", "Lossy", "Lossy & Cap.", 'location','southoutside', 'Orientation','horizontal','FontSize', 10);
hL1.Position(1) = 0.4;
hL1.Position(2) = 0.01;

% Guardar la figura
exportgraphics(h1, fullfile(result_path, 'fig/fig_fullrandom_global_powers.pdf'));

%% FIGURA 2: Tiempos e Iteraciones
h2 = figure();
set(gcf, 'Position', [100, 100, 1200, 500]);

% Layout para minimizar espacios
tiledlayout(1,2, 'TileSpacing', 'loose', 'Padding', 'loose');

% Subplot 1 - Tiempos de cálculo
nexttile;
plotBarWithErrors(mean(data_avg_all(:, [8 9 10], :), 3), sem_all(:, [8 9 10], :), "Average Total convergence time", "Time (ms)");

% Subplot 2 - Iteraciones necesarias
nexttile;
plotBarWithErrors(mean(data_avg_all(:, [11 12 13], :), 3), sem_all(:, [11 12 13], :), "Average Iterations to convergence", "Number of iterations");

% Crear una leyenda global
hL2 = legend("Ideal", "Lossy", "Lossy & Cap.", 'location','southoutside', 'Orientation','horizontal','FontSize', 10);
hL2.Position(1) = 0.40;
hL2.Position(2) = 0.01;

% Guardar la figura
exportgraphics(h2, fullfile(result_path, 'fig/fig_fullrandom_global_time_iter.pdf'));

%% FIGURAS TEMPORALES

% Intervalo de tiempo en minutos (cada delta representa 15 minutos)
time_vector = datetime(2025, 2, 14, 0, 0, 0) + minutes(15 * (0:(num_deltas-1)));

criteria_labels = {'Hops', 'Low-Link Losses', 'Power2Zero', 'Power2Zero + Losses'};
criteria_markers = {'-o', '-+', '-^', '-*'};
case_titles = {"Ideal", "Lossy", "Lossy & Cap."};

for j = 2:3
    h = figure();
    set(gcf, 'Position', [100 100 1700 1000]);
    tiledlayout(2,1, 'TileSpacing', 'loose', 'Padding', 'loose');
    nexttile;
    hold on;
    box on;
    plot(time_vector, data_avg_power(1, :, 1), '-', 'Color','black', 'LineWidth', 3, 'DisplayName', 'Ideal');
        
    for c = 1:num_criteria
        plot(time_vector, data_avg_power(c, :, j), criteria_markers{c}, 'LineWidth', 1.5, 'DisplayName', criteria_labels{c});
    end
        
    grid on;
    xlabel('Time');
    ylabel('Power (kW)');
    title("Temporal Power Balance - " + case_titles{j});
    hold off;

    nexttile;
    hold on;
    box on;
    plot(time_vector, zeros(1, num_deltas), '-', 'Color','black', 'LineWidth', 3, 'DisplayName', 'Ideal');
    
    for c = 1:num_criteria
        plot(time_vector, abs(data_avg_power(1, :, 1) - data_avg_power(c, :, j)), criteria_markers{c}, 'LineWidth', 1.5, 'DisplayName', criteria_labels{c});
    end
    grid on;
    xlabel('Time');
    ylabel('Power (kW)');
    title("Difference respect Ideal");
    hold off;
    
    legend("Ideal", 'Hops', 'Low-Link Losses', 'Power2Zero', 'Power2Zero + Losses', 'location','southoutside', 'Orientation','horizontal','FontSize', 10);
    exportgraphics(h, fullfile(result_path, strcat('fig/fig_fullrandom_TempPowerBalance_', case_titles{j}, '.pdf')));
end

%% FUNCIÓN AUXILIAR: BARRAS CON ERRORES
function plotBarWithErrors(data_avg, sem, title_str, ylabel_str)
    bar_handle = bar(data_avg, 0.6, 'grouped', 'FaceColor', 'flat'); hold on;
    
    % Error bars
    ngroups = size(data_avg, 1);
    nbars = size(data_avg, 2);
    groupwidth = min(0.6, nbars/(nbars + 1.5));
    
    for i = 1:nbars
        x = bar_handle(i).XEndPoints;
        errorbar(x, data_avg(:, i), sem(:, i), 'k', 'linestyle', 'none', 'CapSize', 10);
    end
    
    grid on;
    title(title_str, 'FontSize', 14);
    ylabel(ylabel_str);
    set(gca, 'XTickLabel', {'Hops', 'Low-Link Losses', 'Power2Zero', 'Power2Zero + Losses'}, 'XTickLabelRotation', 0);

    hold off;
end