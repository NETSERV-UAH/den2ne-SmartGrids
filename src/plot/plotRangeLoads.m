%% plotRangeLoads.m
%
%   [+] Autor: David Carrascal <david.carrascal@uah.es> 
%
%   [+] Fecha:  14 Feb 2025

function plotRangeLoads(init, fin, result_path)
    
    % Preparamos la matriz de datos 
    data3d = zeros(4, 13, fin-init+1); % Se reduce a 4 criterios
    
    % Obtenemos los datos de los ficheros csv indicados
    for i = init:fin
        file_path = fullfile(result_path, strcat("csv/outdata_d", num2str(i), ".csv"));
        data_table = readtable(file_path, 'NumHeaderLines', 1);
        
        % Pasamos a matriz y filtramos los criterios
        data = data_table{:,:};
        selected_criteria = [1, 3, 4, 5]; % Se eliminó el criterio de distancia
        data3d(:, :, i-init+1) = data(selected_criteria, :);
    end
    
    % Obtenemos la media y el error estándar para balance de potencias
    data_avg = mean(data3d(:, [2 4 6], :), 3);
    sem = std(data3d(:, [2 4 6], :), [], 3) / sqrt(fin-init+1);
    
    % Pintamos balance global de potencias
    plotBarWithErrors(data_avg, sem, result_path, 'powerBalance_global.pdf', "Balance de potencias global", "Potencia (kW)");
    
    % Obtenemos la media y el error estándar para flujo absoluto de potencia
    data_avg_flux = mean(data3d(:, [3 5 7], :), 3);
    sem_flux = std(data3d(:, [3 5 7], :), [], 3) / sqrt(fin-init+1);
    
    % Pintamos flujo absoluto de potencia
    plotBarWithErrors(data_avg_flux, sem_flux, result_path, 'powerAbsFlux_global.pdf', "Valor absoluto del flujo de potencias", "Potencia (kW)");
    
    % Obtenemos la media y el error estándar para tiempos de cálculo
    time_avg = mean(data3d(:, [8 9 10], :), 3);
    sem_time = std(data3d(:, [8 9 10], :), [], 3) / sqrt(fin-init+1);
    
    % Pintamos tiempos de cálculo
    plotBarWithErrors(time_avg, sem_time, result_path, 'timestamps_global.pdf', "Tiempos de cálculo", "Tiempo (ms)");

    % Obtenemos la media y el error estándar para las iteraciones
    iter_avg = mean(data3d(:, [11 12 13], :), 3);
    sem_iter = std(data3d(:, [11 12 13], :), [], 3) / sqrt(fin-init+1);
    
    % Pintamos tiempos de cálculo
    plotBarWithErrors(iter_avg, sem_iter, result_path, 'iter_global.pdf', "Iteraciones por criterio", "Num iter.");
end

function plotBarWithErrors(data_avg, sem, result_path, filename, title_str, ylabel_str)
    h = figure();
    set(gcf, 'Position', [100 100 900 700]);
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
    title(title_str, 'FontSize', 16);
    ylabel(ylabel_str);
    legend("Ideal", "Con pérdidas", "Con pérdidas y capacidades", 'Location', 'southoutside', 'NumColumns', 3);
    set(gca, 'XTickLabel', {'Hops', 'Pérdidas', 'Potencia 0', 'Potencia 0 + Pérdidas'});
    hold off;
    
    % Exportamos la gráfica
    exportgraphics(h, fullfile(result_path, strcat('fig/', filename)));
end
